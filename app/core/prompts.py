"""
app/core/prompts.py — Construction des prompts LLM

CORRECTIONS v3 :
- Prompt arabe : instruction de langue beaucoup plus stricte
  + exemple de format attendu pour guider le modèle
  + interdiction explicite des mots étrangers avec liste d'exemples
- Prompt français : légèrement allégé pour gagner en vitesse
- Contexte toujours tronqué à 1200 chars (inchangé)
"""


def build_prompt(
    question: str,
    lang: str,
    full_context: str,
    conversation_context: str = "",
) -> str:
    if lang == "ar":
        return _prompt_ar(question, full_context, conversation_context)
    return _prompt_fr(question, full_context, conversation_context)


def _prompt_ar(question: str, ctx: str, conv: str) -> str:
    mem = f"\n[سياق المحادثة]\n{conv[:400]}\n" if conv.strip() else ""
    ctx_truncated = ctx[:1200] if len(ctx) > 1200 else ctx

    return f"""أنت محامٍ خبير في القانون العقاري التونسي. مهمتك: الإجابة بالعربية الفصحى فقط.

══ قواعد صارمة ══
1. اكتب بالعربية الفصحى فقط. ممنوع تمامًا استخدام أي كلمة فرنسية أو إنجليزية.
2. المصطلحات القانونية الفرنسية تُترجم بالعربية:
   - "titre foncier" → رسم عقاري
   - "non-hypothèque" → شهادة عدم التحميل
   - "TIB" → ضريبة الأملاك المبنية
   - "CPF" → رسم الصندوق العقاري
   - "notaire" → كاتب العدل
   - "huissier" → المحضر القضائي
   - "registre foncier" → السجل العقاري
3. الشكل المطلوب حرفيًا:

**عنوان الموضوع**

1. **العنصر الأول:** شرح واضح بالعربية فقط.
2. **العنصر الثاني:** شرح واضح بالعربية فقط.
3. **العنصر الثالث:** شرح واضح بالعربية فقط.

**تنبيه:** تنبيه قانوني واحد.

4. لا تكرار. لا تخترع فصولاً قانونية. إذا لم تجد المعلومة في النص، قل ذلك بالعربية.
{mem}
══ النصوص القانونية المرجعية ══
{ctx_truncated}
══ نهاية النصوص ══

{question}

الجواب:"""


def _prompt_fr(question: str, ctx: str, conv: str) -> str:
    mem = f"\n[Contexte]\n{conv[:400]}\n" if conv.strip() else ""
    ctx_truncated = ctx[:1200] if len(ctx) > 1200 else ctx

    return f"""Tu es un avocat expert en droit immobilier tunisien. Réponds en français uniquement.

Règles : titre + 3 à 5 points numérotés + 1 avertissement si nécessaire.
Pas de répétition. Pas d'article inventé. Si l'information manque, dis-le clairement.
{mem}
=== TEXTES JURIDIQUES ===
{ctx_truncated}
=== FIN ===

{question}

RÉPONSE:"""