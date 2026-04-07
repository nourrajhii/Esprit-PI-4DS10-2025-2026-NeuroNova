"""
app/services/llm.py — Appel au LLM Ollama + post-traitement réponse

CORRECTIFS :
- _llm_instance : singleton — OllamaLLM créé une seule fois, réutilisé partout
- Timeout explicite pour éviter les blocages silencieux
- BUGFIX : dedup_point utilisait m.group(1) sans groupe capturant → IndexError
- BUGFIX : renumber utilisait m.group(1) sans groupe capturant → même erreur potentielle
"""
import re
from app.core.config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS

# ── Singleton LLM ──────────────────────────────────────────────────────────────

_llm_instance = None


def get_llm():
    """
    Retourne l'instance OllamaLLM (créée une seule fois au premier appel).
    Réutiliser la même instance évite le coût d'initialisation à chaque requête.
    """
    global _llm_instance
    if _llm_instance is None:
        from langchain_ollama import OllamaLLM
        _llm_instance = OllamaLLM(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            num_predict=LLM_MAX_TOKENS,
            timeout=120,
            stop=[
                "\n\nQuestion :", "QUESTION :", "السؤال :",
                "\nالنقطة السادسة", "\n6.", "\n7.", "\n8.", "\n9.",
            ],
        )
    return _llm_instance


def reset_llm():
    """Force la recréation de l'instance LLM (utile si Ollama redémarre)."""
    global _llm_instance
    _llm_instance = None


# ── Utilitaires ────────────────────────────────────────────────────────────────

def _similar(a: str, b: str, threshold: float = 0.6) -> bool:
    """Compare deux chaînes normalisées — retourne True si trop similaires."""
    if not a or not b:
        return False
    wa = set(a.split())
    wb = set(b.split())
    if not wa or not wb:
        return False
    return (len(wa & wb) / len(wa | wb)) >= threshold


def clean_response(text: str, lang: str) -> str:
    """Nettoie, déduplique et tronque la réponse du LLM."""

    # 1. Supprimer les en-têtes vides arabes
    text = re.sub(
        r'\n(النقطة\s+(الأولى|الثانية|الثالثة|الرابعة|الخامسة'
        r'|السادسة|السابعة))\s*\n',
        '\n', text
    )

    # 2. Supprimer numéros > 5
    text = re.sub(r'\n[6-9]\.\s+', '\n', text)
    text = re.sub(r'\n1[0-9]\.\s+', '\n', text)

    # 3. Pour l'arabe : retirer les mots français/latins intégrés
    if lang == "ar":
        fr_to_ar = {
            r'\bhuissier\b':               'محضر قضائي',
            r'\bmise en demeure\b':         'إنذار رسمي',
            r'\bjuge cantonal\b':           'القاضي الكانتوني',
            r'\baudience contradictoire\b': 'جلسة تناقضية',
            r'\bjugement\b':               'حكم قضائي',
            r'\bsaisine\b':                'إحالة',
            r'\bdélai légal\b':            'الأجل القانوني',
            r'\bcontrat\b':                'عقد',
            r'\blocataire\b':              'المستأجر',
            r'\bpropriétaire\b':           'المالك',
            r'\bloyer\b':                  'الإيجار',
        }
        for pattern, replacement in fr_to_ar.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        text = re.sub(r'\b[a-zA-Zéèêëàâùûüïîôœç]{4,}\b', '', text)
        text = re.sub(r'  +', ' ', text)

    # 4. Dédupliquer les lignes avec similarité
    lines = text.split("\n")
    deduped = []
    seen_norms = []
    for line in lines:
        norm = re.sub(r'\s+', ' ', line.strip().lower())
        if not norm or norm.startswith("**") or norm.startswith("#"):
            deduped.append(line)
            continue
        if not any(_similar(norm, s) for s in seen_norms):
            deduped.append(line)
            seen_norms.append(norm)
    text = "\n".join(deduped)

    # 5. Dédupliquer les points numérotés (1. 2. 3. ...)
    # BUGFIX : pattern avec DEUX groupes capturants pour accéder séparément
    # au préfixe numérique (group 1) et au contenu (group 2)
    seen_points: list[str] = []

    def dedup_point(m: re.Match) -> str:
        # group(1) = "1. "   group(2) = contenu du point
        content = re.sub(r'\s+', ' ', m.group(2).strip().lower())
        if any(_similar(content, s) for s in seen_points):
            return ""   # supprimer ce point dupliqué
        seen_points.append(content)
        return m.group(0)   # garder tel quel, on renumérotera ensuite

    text = re.sub(r'^(\d+\.\s+)(.+)$', dedup_point, text, flags=re.MULTILINE)

    # 6. Renuméroter les points restants
    counter = [0]

    def renumber(m: re.Match) -> str:
        counter[0] += 1
        return f"{counter[0]}. {m.group(2)}"

    text = re.sub(r'^(\d+\.\s+)(.+)$', renumber, text, flags=re.MULTILINE)

    # 7. Nettoyer les lignes vides multiples
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 8. Tronquer si trop long
    non_empty = [l for l in text.split("\n") if l.strip()]
    if len(non_empty) > 20:
        text = "\n".join(non_empty[:20])
        suffix = ("⚠️ للمزيد، استشر محامياً أو كاتب عدل." if lang == "ar"
                  else "⚠️ Pour plus de détails, consultez un avocat ou notaire.")
        text += f"\n\n{suffix}"

    return text.strip()