"""
app/services/rag.py — Orchestrateur RAG principal

CORRECTIONS v3 :
- Filtrage FAISS post-retrieval par metadata["parent"] selon question_type
- Ajout couche NLP : re-ranking sémantique par TF-IDF + Jaccard avant appel LLM
- Déduplication des chunks similaires avant injection dans le prompt
- Fallback robuste si filtre thématique trop restrictif
- Score NLP exposé dans les métriques
"""
import re
import math
from collections import Counter

from app.core.config import SELF_CONTAINED_TYPES, SIMILARITY_SEUIL, SIMILARITY_SEUIL_LOW
from app.core.language import detect_language, detect_question_type
from app.core.prompts import build_prompt
from app.services.calculator import is_calculation_question, handle_calculation
from app.services.hardcoded import (
    HARDCODED_RULES, HARDCODED_SOURCE_LABELS,
    DROITS_REELS_RULES, LEGALITE_BIEN_RULES,
)
from app.services.vector_store import (
    get_db, get_source_info, normalize_score, score_label, extract_article_refs,
)
from app.services.llm import get_llm, call_gemini, clean_response
from app.services.cache import lookup as cache_lookup, store as cache_store

# ── Mapping type de question → sources FAISS autorisées ───────────────────────
# Clés = valeurs possibles de metadata["parent"] ou metadata["file"]
QUESTION_TYPE_TO_SOURCES: dict[str, set[str]] = {
    "droits_reels": {"droit_reel", "loi"},
    "urbanisme":    {"urbanisme.pdf"},
    "coc":          {"COC.pdf", "droit_reel", "loi"},   # includes TXT fragments with notaire/contrat info
    "documents":    {"loi_location", "droit_reel", "loi"},
    "expulsion":    {"loi_location", "COC.pdf"},
    "bailleur":     {"loi_location", "COC.pdf"},
    "plus_value":   {"loi", "COC.pdf"},
    "legalite_bien":{"droit_reel", "loi"},
    "fiscal":       set(),   # hardcoded suffit → pas de filtre FAISS
    "general":      set(),   # pas de filtre → toutes sources acceptées
    "chitchat":     set(),
}

# ── Réponses chitchat ──────────────────────────────────────────────────────────
_CHITCHAT_RESPONSES = {
    "fr": (
        "Bonjour ! Je suis votre assistant juridique immobilier tunisien. "
        "Posez-moi une question sur le droit immobilier, la fiscalité, les baux, "
        "les permis de construire ou les droits réels."
    ),
    "ar": (
        "مرحباً ! أنا مساعدك القانوني في مجال العقارات التونسية. "
        "اطرح عليّ سؤالاً حول القانون العقاري، الضرائب، عقود الكراء، "
        "رخص البناء أو الحقوق العينية."
    ),
}


def _chitchat_response(lang: str) -> dict:
    return {
        "answer":           _CHITCHAT_RESPONSES.get(lang, _CHITCHAT_RESPONSES["fr"]),
        "metrics":          [],
        "hardcoded_source": {"icon": "⚖️", "label": "Assistant juridique"},
        "question_type":    "chitchat",
        "lang":             lang,
        "is_calculation":   False,
        "from_cache":       False,
    }


# ── Couche NLP : TF-IDF léger + re-ranking ────────────────────────────────────

def _tokenize_nlp(text: str) -> list[str]:
    """Tokenisation simple bilingue ar/fr — retire stopwords courants."""
    STOPWORDS_FR = {
        "le", "la", "les", "de", "du", "des", "un", "une", "et", "en",
        "que", "qui", "est", "dans", "pour", "sur", "par", "avec", "ce",
        "se", "il", "elle", "son", "sa", "ses", "au", "aux", "ou", "je",
        "tu", "nous", "vous", "ils", "elles", "pas", "plus", "très",
    }
    STOPWORDS_AR = {
        "في", "من", "إلى", "على", "عن", "مع", "هذا", "هذه", "ذلك",
        "التي", "الذي", "أن", "كان", "قد", "لا", "ما", "هو", "هي",
        "لم", "لن", "كل", "بعض", "حيث", "إذا", "ثم", "أو", "و",
    }
    text = text.lower()
    text = re.sub(r'[\u0610-\u061A\u064B-\u065F]', '', text)   # diacritiques
    text = re.sub(r'[أإآٱ]', 'ا', text)
    text = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', text)
    tokens = [t for t in text.split() if len(t) >= 2]
    return [t for t in tokens if t not in STOPWORDS_FR and t not in STOPWORDS_AR]


def _tfidf_score(query_tokens: list[str], doc_text: str, corpus_size: int = 50) -> float:
    """
    Score TF-IDF simplifié entre la requête et un document.
    corpus_size = estimation du nb de chunks dans l'index.
    """
    doc_tokens = _tokenize_nlp(doc_text)
    if not doc_tokens or not query_tokens:
        return 0.0

    doc_freq = Counter(doc_tokens)
    doc_len = len(doc_tokens)
    score = 0.0

    for token in set(query_tokens):
        tf = doc_freq.get(token, 0) / doc_len
        # IDF simplifié : pénalise les tokens trop courants
        df_estimate = max(1, sum(1 for t in query_tokens if t == token))
        idf = math.log((corpus_size + 1) / (df_estimate + 1)) + 1
        score += tf * idf

    return round(score, 4)


def _jaccard_nlp(q_tokens: set, doc_tokens: set) -> float:
    """Similarité Jaccard entre ensembles de tokens."""
    if not q_tokens or not doc_tokens:
        return 0.0
    inter = len(q_tokens & doc_tokens)
    union = len(q_tokens | doc_tokens)
    return round(inter / union, 4) if union else 0.0


def _nlp_rerank(question: str, docs_scores: list) -> list:
    """
    Re-rank les chunks récupérés par FAISS en combinant :
      - score FAISS normalisé (poids 0.5)
      - score TF-IDF  (poids 0.3)
      - similarité Jaccard (poids 0.2)
    Retourne la liste triée par score combiné décroissant.
    """
    q_tokens = _tokenize_nlp(question)
    q_set = set(q_tokens)
    reranked = []

    for doc, raw_score in docs_scores:
        faiss_sim = normalize_score(raw_score)
        tfidf = _tfidf_score(q_tokens, doc.page_content)
        # Normaliser tfidf entre 0 et 1 (cap à 2.0 = score max estimé)
        tfidf_norm = min(tfidf / 2.0, 1.0)
        doc_tokens_set = set(_tokenize_nlp(doc.page_content))
        jaccard = _jaccard_nlp(q_set, doc_tokens_set)

        combined = round(
            0.50 * faiss_sim +
            0.30 * tfidf_norm +
            0.20 * jaccard,
            4
        )
        reranked.append((doc, raw_score, combined, tfidf_norm, jaccard))

    reranked.sort(key=lambda x: x[2], reverse=True)
    return reranked


def _deduplicate_chunks(reranked: list, threshold: float = 0.70) -> list:
    """
    Supprime les chunks trop similaires entre eux (Jaccard > threshold).
    Garde toujours le chunk avec le meilleur score combiné.
    """
    kept = []
    for item in reranked:
        doc = item[0]
        doc_tokens = set(_tokenize_nlp(doc.page_content))
        is_dup = False
        for kept_item in kept:
            kept_tokens = set(_tokenize_nlp(kept_item[0].page_content))
            if _jaccard_nlp(doc_tokens, kept_tokens) >= threshold:
                is_dup = True
                break
        if not is_dup:
            kept.append(item)
    return kept


# ── Fallback sans LLM : synthèse directe depuis les chunks BM25 pré-rankés ────

def _fallback_answer_from_metrics(question: str, metrics: list, lang: str) -> str:
    """
    Construit une réponse depuis les chunks BM25 déjà rankés (metrics list).
    Évite de re-scorer full_context qui mélange règles hardcodées + chunks réels.
    Extrait les phrases les plus pertinentes de chaque chunk et les formate.
    """
    if not metrics:
        if lang == "ar":
            return "عذراً، لا تتوفر معلومات كافية للإجابة على هذا السؤال حالياً."
        return "Aucune information pertinente trouvée dans la base juridique pour cette question."

    q_tokens = set(_tokenize_nlp(question))

    selected_parts = []
    seen_tokens: list[set] = []

    for m in metrics:
        doc = m.get("_doc")
        if doc is None:
            continue
        content = doc.page_content.strip()
        source = m.get("source", "inconnu")

        # Découper le chunk en phrases/paragraphes
        sentences = [s.strip() for s in re.split(r'\n+|(?<=[.!?؟])\s+', content) if len(s.strip()) > 30]
        if not sentences:
            sentences = [content]

        # Scorer chaque phrase par rapport à la question
        scored_sents = []
        for sent in sentences:
            sent_tokens = set(_tokenize_nlp(sent))
            jac = _jaccard_nlp(q_tokens, sent_tokens)
            tfidf = _tfidf_score(list(q_tokens), sent)
            score = 0.6 * jac + 0.4 * min(tfidf / 2.0, 1.0)
            scored_sents.append((score, sent))

        scored_sents.sort(key=lambda x: x[0], reverse=True)

        # Prendre les 2 meilleures phrases non-redondantes de ce chunk
        chunk_parts = []
        for score, sent in scored_sents:
            sent_tok = set(_tokenize_nlp(sent))
            if any(_jaccard_nlp(sent_tok, s) > 0.65 for s in seen_tokens):
                continue
            chunk_parts.append(sent)
            seen_tokens.append(sent_tok)
            if len(chunk_parts) >= 2:
                break

        if chunk_parts:
            label = m.get("source_label") or source
            selected_parts.append((label, chunk_parts, m.get("nlp_combined", 0)))

        if len(selected_parts) >= 4:
            break

    if not selected_parts:
        # Fallback ultime : prendre le texte brut du premier chunk
        for m in metrics[:2]:
            doc = m.get("_doc")
            if doc:
                selected_parts.append((
                    m.get("source_label", m.get("source", "")),
                    [doc.page_content[:400].strip()],
                    m.get("nlp_combined", 0),
                ))

    if not selected_parts:
        if lang == "ar":
            return "عذراً، لا تتوفر معلومات كافية للإجابة على هذا السؤال حالياً."
        return "Aucune information pertinente trouvée dans la base juridique pour cette question."

    if lang == "ar":
        header = "**بناءً على النصوص القانونية التونسية:**\n\n"
        footer = "\n\n⚠️ *هذه إجابة تلقائية بدون نموذج ذكاء اصطناعي. استشر محامياً للتأكيد.*"
    else:
        header = "**Sur la base des textes juridiques tunisiens :**\n\n"
        footer = "\n\n⚠️ *Réponse extraite directement des textes (LLM hors ligne). Consultez un professionnel pour confirmation.*"

    blocks = []
    for label, parts, score in selected_parts:
        block = f"**[{label}]**\n" + "\n".join(f"• {p}" for p in parts)
        blocks.append(block)

    return header + "\n\n".join(blocks) + footer


# ── Orchestrateur principal ────────────────────────────────────────────────────

def ask_with_metrics(
    question: str,
    k: int = 5,
    conversation_context: str = "",
) -> dict:

    lang          = detect_language(question)
    question_type = detect_question_type(question)
    is_calc       = is_calculation_question(question)

    # ── 1. Chitchat ───────────────────────────────────────────
    if question_type == "chitchat":
        return _chitchat_response(lang)

    skip_cache = (is_calc and bool(re.search(r'\d{3,}', question))) \
                 or bool(conversation_context.strip())

    # ── 2. Cache ──────────────────────────────────────────────
    if not skip_cache:
        cached = cache_lookup(question)
        if cached:
            return cached

    result = {
        "answer":           "",
        "metrics":          [],
        "hardcoded_source": None,
        "question_type":    question_type,
        "lang":             lang,
        "is_calculation":   is_calc,
        "from_cache":       False,
    }

    # ── 3. Calculs directs ────────────────────────────────────
    if is_calc:
        calc = handle_calculation(question, lang)
        if calc:
            result["answer"] = calc
            icon, label = HARDCODED_SOURCE_LABELS.get(
                question_type, HARDCODED_SOURCE_LABELS["fiscal"]
            )
            result["hardcoded_source"] = {"icon": icon, "label": label}
            if not skip_cache:
                cache_store(question, result)
            return result

    # ── 4. Contexte hardcodé ──────────────────────────────────
    extra = HARDCODED_RULES.get(question_type, "")
    if extra:
        icon, label = HARDCODED_SOURCE_LABELS.get(
            question_type, HARDCODED_SOURCE_LABELS["general"]
        )
        result["hardcoded_source"] = {"icon": icon, "label": label}

    # ── 5. FAISS + NLP re-ranking ─────────────────────────────
    rag_context = ""
    db = get_db()

    # Query expansion: augment query with domain-specific keywords
    _TYPE_EXPANSIONS = {
        "coc":          "acte authentique notaire contrat vente obligation garantie",
        "documents":    "document pièce dossier acte enregistrement foncier",
        "droits_reels": "propriété hypothèque usufruit servitude registre foncier",
        "expulsion":    "bail loyer locataire expulsion résiliation mise en demeure",
        "bailleur":     "bailleur obligation réparation vice caché loyer",
        "legalite_bien":"titre foncier légalité vérification hypothèque charge",
        "urbanisme":    "permis construire zone urbanisme conformité bâtiment",
    }
    expansion = _TYPE_EXPANSIONS.get(question_type, "")
    retrieval_query = f"{question} {expansion}".strip() if expansion else question

    if db:
        try:
            # Récupérer k*3 chunks pour compenser le filtre thématique
            fetch_k = k * 3
            docs_scores_raw = db.similarity_search_with_score(retrieval_query, k=fetch_k)

            # ── Filtre thématique par metadata["parent"] / "file" ──
            allowed = QUESTION_TYPE_TO_SOURCES.get(question_type, set())
            if allowed:
                filtered = [
                    (doc, score) for doc, score in docs_scores_raw
                    if doc.metadata.get("parent", doc.metadata.get("file", "")) in allowed
                ]
                # Fallback : si filtre trop restrictif (<2 résultats), on désactive
                if len(filtered) < 2:
                    filtered = docs_scores_raw
                docs_scores_filtered = filtered
            else:
                docs_scores_filtered = docs_scores_raw

            # ── NLP re-ranking ─────────────────────────────────────
            reranked = _nlp_rerank(question, docs_scores_filtered)

            # ── Pénalité sources non-pertinentes ───────────────────
            # 08_loi17_avantages_fiscaux.txt est un dump fiscal/loyer
            # → pénaliser si la question n'est pas fiscal/location/bailleur
            _FISCAL_DUMP_FILES = {"08_loi17_avantages_fiscaux.txt"}
            # Only keep 08_loi17 unpenalized for pure fiscal/tax questions
            _FISCAL_TYPES = {"fiscal", "plus_value"}
            if question_type not in _FISCAL_TYPES:
                penalized = []
                for doc, raw_score, combined, tfidf_norm, jaccard in reranked:
                    fname = doc.metadata.get("file", "")
                    if fname in _FISCAL_DUMP_FILES:
                        combined = round(combined * 0.55, 4)  # heavy penalty
                    penalized.append((doc, raw_score, combined, tfidf_norm, jaccard))
                penalized.sort(key=lambda x: x[2], reverse=True)
                reranked = penalized

            # ── Déduplication des chunks similaires ────────────────
            reranked = _deduplicate_chunks(reranked, threshold=0.70)

            # ── Limiter au k final ─────────────────────────────────
            reranked = reranked[:k]

            # ── Construction des métriques ─────────────────────────
            metrics = []
            for rank, (doc, raw_score, combined, tfidf_norm, jaccard) in enumerate(reranked, start=1):
                sim = normalize_score(raw_score)
                s_emoji, s_label = score_label(combined)   # utiliser score combiné
                file_name = doc.metadata.get("file", "inconnu")
                src = get_source_info(file_name)
                raw_snippet = doc.page_content.replace("\n", " ").strip()
                snippet = raw_snippet[:120] + ("…" if len(raw_snippet) > 120 else "")
                metrics.append({
                    "rank":         rank,
                    "source":       file_name,
                    "source_label": src["label"],
                    "source_short": src["short"],
                    "source_icon":  src["icon"],
                    "raw_score":    round(float(raw_score), 4),
                    "similarity":   sim,
                    "nlp_combined": combined,    # score NLP combiné
                    "nlp_tfidf":    round(tfidf_norm, 3),
                    "nlp_jaccard":  round(jaccard, 3),
                    "score_emoji":  s_emoji,
                    "score_label":  s_label,
                    "article_refs": extract_article_refs(doc.page_content),
                    "snippet":      snippet,
                    "_doc":         doc,
                })

            result["metrics"] = metrics

            # ── Sélection des chunks pertinents pour le contexte ───
            if question_type not in SELF_CONTAINED_TYPES:
                seuil = (
                    SIMILARITY_SEUIL_LOW
                    if question_type in ("urbanisme", "coc", "documents", "expulsion", "bailleur", "legalite_bien")
                    else SIMILARITY_SEUIL
                )
                # Utiliser nlp_combined plutôt que similarity seule
                relevant = [
                    m["_doc"] for m in metrics
                    if m["nlp_combined"] >= seuil
                ]
                # Si aucun chunk ne dépasse le seuil, prendre les 3 meilleurs quand même
                if not relevant and metrics:
                    relevant = [m["_doc"] for m in metrics[:3]]
                if relevant:
                    # Tronquer chaque chunk pour éviter un prompt trop long
                    rag_context = "\n\n".join(
                        d.page_content[:600] for d in relevant
                    )

        except Exception as e:
            print(f"⚠️ Erreur FAISS/NLP : {e}")

    # ── 6. Contexte final ─────────────────────────────────────
    full_context = f"{extra}\n\n{rag_context}".strip() if rag_context else extra
    if not full_context:
        full_context = DROITS_REELS_RULES + "\n\n" + LEGALITE_BIEN_RULES
        result["hardcoded_source"] = {"icon": "📚", "label": "Base juridique générale"}

    # ── 7. Appel LLM (avec fallback sans Ollama) ──────────────
    prompt = build_prompt(
        question=question,
        lang=lang,
        full_context=full_context,
        conversation_context=conversation_context,
    )
    try:
        raw_answer = get_llm().invoke(prompt)
        result["answer"] = clean_response(raw_answer, lang)
    except Exception as llm_err:
        print(f"⚠️ Ollama indisponible ({llm_err}) — tentative Gemini")
        try:
            raw_answer = call_gemini(prompt)
            cleaned = clean_response(raw_answer, lang)
            print(f"✅ Gemini réponse obtenue ({len(cleaned)} chars)")
            result["answer"] = cleaned
            result["hardcoded_source"] = result.get("hardcoded_source") or {
                "icon": "✨", "label": "Gemini Flash"
            }
        except Exception as gemini_err:
            print(f"⚠️ Gemini indisponible ({gemini_err}) — fallback extraction BM25")
            result["answer"] = _fallback_answer_from_metrics(question, result["metrics"], lang)
            result["hardcoded_source"] = result.get("hardcoded_source") or {
                "icon": "📚", "label": "Extraction directe (LLM hors ligne)"
            }

    # Guard: never return an empty answer
    if not result["answer"].strip():
        result["answer"] = (
            "عذراً، لا تتوفر معلومات كافية للإجابة على هذا السؤال حالياً. يُرجى إعادة الصياغة."
            if lang == "ar"
            else "Désolé, aucune réponse n'a pu être générée pour cette question. Essayez de la reformuler."
        )

    if not skip_cache:
        cache_store(question, result)

    return result


def ask(question: str, k: int = 3) -> str:
    return ask_with_metrics(question, k=k)["answer"]