"""
app/services/rag.py — Orchestrateur RAG principal

Flux :
  1. Chitchat → réponse immédiate (pas de LLM juridique)
  2. Calcul   → réponse directe
  3. Cache    → réponse instantanée si similaire
  4. Contexte hardcodé + FAISS → prompt LLM → réponse
"""
import re

from app.core.config import SELF_CONTAINED_TYPES, SIMILARITY_SEUIL, SIMILARITY_SEUIL_LOW
from app.core.language import detect_language, detect_question_type
from app.core.prompts import build_prompt
from app.services.calculator import is_calculation_question, handle_calculation
from app.services.hardcoded import HARDCODED_RULES, HARDCODED_SOURCE_LABELS, DROITS_REELS_RULES, LEGALITE_BIEN_RULES
from app.services.vector_store import get_db, get_source_info, normalize_score, score_label, extract_article_refs
from app.services.llm import get_llm, clean_response
from app.services.cache import lookup as cache_lookup, store as cache_store

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


# ── Orchestrateur principal ────────────────────────────────────────────────────

def ask_with_metrics(
    question: str,
    k: int = 5,
    conversation_context: str = "",
) -> dict:

    lang          = detect_language(question)
    question_type = detect_question_type(question)
    is_calc       = is_calculation_question(question)

    # ── 1. Chitchat — réponse immédiate ──────────────────────
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
            icon, label = HARDCODED_SOURCE_LABELS.get(question_type, HARDCODED_SOURCE_LABELS["fiscal"])
            result["hardcoded_source"] = {"icon": icon, "label": label}
            if not skip_cache:
                cache_store(question, result)
            return result

    # ── 4. Contexte hardcodé ──────────────────────────────────
    extra = HARDCODED_RULES.get(question_type, "")
    if extra:
        icon, label = HARDCODED_SOURCE_LABELS.get(question_type, HARDCODED_SOURCE_LABELS["general"])
        result["hardcoded_source"] = {"icon": icon, "label": label}

    # ── 5. FAISS ──────────────────────────────────────────────
    rag_context = ""
    db = get_db()
    if db:
        try:
            docs_scores = db.similarity_search_with_score(question, k=k)
            metrics = []
            for rank, (doc, raw_score) in enumerate(docs_scores, start=1):
                sim = normalize_score(raw_score)
                s_emoji, s_label = score_label(sim)
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
                    "score_emoji":  s_emoji,
                    "score_label":  s_label,
                    "article_refs": extract_article_refs(doc.page_content),
                    "snippet":      snippet,
                    "_doc":         doc,
                })
            metrics.sort(key=lambda x: x["similarity"], reverse=True)
            result["metrics"] = metrics

            if question_type not in SELF_CONTAINED_TYPES:
                seuil = SIMILARITY_SEUIL_LOW if question_type in ("urbanisme", "coc") else SIMILARITY_SEUIL
                relevant = [m["_doc"] for m in metrics if m["similarity"] >= seuil]
                if relevant:
                    rag_context = "\n\n".join(d.page_content for d in relevant)

        except Exception as e:
            print(f"⚠️ Erreur FAISS : {e}")

    # ── 6. Contexte final ─────────────────────────────────────
    full_context = f"{extra}\n\n{rag_context}".strip() if rag_context else extra
    if not full_context:
        full_context = DROITS_REELS_RULES + "\n\n" + LEGALITE_BIEN_RULES
        result["hardcoded_source"] = {"icon": "📚", "label": "Base juridique générale"}

    # ── 7. Appel LLM ──────────────────────────────────────────
    prompt = build_prompt(
        question=question,
        lang=lang,
        full_context=full_context,
        conversation_context=conversation_context,
    )
    raw_answer = get_llm().invoke(prompt)
    result["answer"] = clean_response(raw_answer, lang)

    if not skip_cache:
        cache_store(question, result)

    return result


def ask(question: str, k: int = 3) -> str:
    return ask_with_metrics(question, k=k)["answer"]
