"""
app/core/prompts.py — Construction des prompts LLM

CORRECTIFS PERFORMANCE :
- Contexte tronqué à 1200 chars (au lieu de 2000) → réponse ~40% plus rapide
- Instructions du prompt allégées (moins de tokens = moins de temps de génération)
- LLM_MAX_TOKENS à 250 suffit pour 3-5 points structurés
"""


def build_prompt(question: str, lang: str, full_context: str,
                 conversation_context: str = "") -> str:
    if lang == "ar":
        return _prompt_ar(question, full_context, conversation_context)
    return _prompt_fr(question, full_context, conversation_context)


def _prompt_ar(question: str, ctx: str, conv: str) -> str:
    mem = f"\n[سياق]\n{conv[:400]}\n" if conv.strip() else ""
    # 1200 chars max — suffisant pour 2-3 articles de loi pertinents
    ctx_truncated = ctx[:1200] if len(ctx) > 1200 else ctx
    return f"""أنت محامٍ خبير في القانون العقاري التونسي. أجب بالعربية فقط.

القواعد:
- العربية فقط، لا فرنسية.
- الشكل: عنوان + 3 إلى 5 نقاط مرقمة + تنبيه واحد إن لزم.
- لا تكرار، لا اختلاق فصول.
{mem}
=== النصوص ===
{ctx_truncated}
=== نهاية ===

{question}

الجواب:"""


def _prompt_fr(question: str, ctx: str, conv: str) -> str:
    mem = f"\n[Contexte]\n{conv[:400]}\n" if conv.strip() else ""
    # 1200 chars max — suffisant pour 2-3 articles de loi pertinents
    ctx_truncated = ctx[:1200] if len(ctx) > 1200 else ctx
    return f"""Tu es un avocat expert en droit immobilier tunisien. Réponds en français uniquement.

Règles: titre + 3 à 5 points numérotés + 1 avertissement si nécessaire. Pas de répétition, pas d'article inventé.
{mem}
=== TEXTES ===
{ctx_truncated}
=== FIN ===

{question}

RÉPONSE:"""