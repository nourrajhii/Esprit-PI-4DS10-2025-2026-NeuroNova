"""
app/services/llm.py — Appel LLM : Ollama (local) avec fallback Gemini (cloud)
"""
import os
import re
import json
import urllib.request
import urllib.error

# Load .env from project root so GEMINI_API_KEY is always available
try:
    from dotenv import load_dotenv as _load_dotenv
    _here = os.path.dirname(os.path.abspath(__file__))
    _load_dotenv(os.path.join(_here, "..", "..", "..", "..", ".env"), override=False)  # project root
except ImportError:
    pass

from app.core.config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS

# ── Gemini config ──────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODELS  = ["gemini-2.5-flash-lite", "gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-2.5-flash"]


# ── Ollama singleton ───────────────────────────────────────────────────────────

_llm_instance = None


def get_llm():
    global _llm_instance
    if _llm_instance is None:
        from langchain_ollama import OllamaLLM
        _llm_instance = OllamaLLM(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            num_predict=LLM_MAX_TOKENS,
            timeout=60,
            stop=[
                "\n\nQuestion :", "QUESTION :", "السؤال :",
                "\nالنقطة السادسة", "\n6.", "\n7.", "\n8.", "\n9.",
            ],
        )
    return _llm_instance


def reset_llm():
    global _llm_instance
    _llm_instance = None


# ── Gemini fallback ────────────────────────────────────────────────────────────

def call_gemini(prompt: str) -> str:
    """Call Gemini via REST, trying each model in GEMINI_MODELS until one succeeds."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": LLM_TEMPERATURE,
            "maxOutputTokens": 800,
            "stopSequences": ["\n\nQuestion :"],
        },
    }).encode("utf-8")

    last_err: Exception = RuntimeError("No models tried")
    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError(f"Gemini {model}: no candidates — {data}")
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts).strip()
            if text:
                print(f"✅ Gemini répondu via {model}")
                return text
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429:
                print(f"⚠️ Gemini {model} rate-limited, essai suivant…")
                continue
            raise
    raise last_err


# ── Dictionnaire de traduction fr → ar ────────────────────────────────────────

_FR_TO_AR: dict[str, str] = {
    r'\bhuissier\b':                  'محضر قضائي',
    r'\bnotaire\b':                   'كاتب عدل',
    r'\bjuge cantonal\b':             'قاضي الناحية',
    r'\bjuge\b':                      'قاضٍ',
    r'\bavocat\b':                    'محامٍ',
    r'\bpromoteur\b':                 'باعث عقاري',
    r'\bcréancier\b':                 'دائن',
    r'\bdébiteur\b':                  'مدين',
    r'\bhéritier\b':                  'وارث',
    r'\bmise en demeure\b':           'إنذار رسمي',
    r'\baudience contradictoire\b':   'جلسة تناقضية',
    r'\bjugement\b':                  'حكم قضائي',
    r'\bsaisine\b':                   'إحالة',
    r'\bexpulsion\b':                 'طرد / إخلاء',
    r'\bexécution forcée\b':          'تنفيذ قسري',
    r'\bdélai légal\b':               'الأجل القانوني',
    r'\brecours\b':                   'طعن',
    r'\bappel\b':                     'استئناف',
    r'\bcontrat\b':                   'عقد',
    r'\bacte notarié\b':              'عقد رسمي',
    r'\bpromesse de vente\b':         'وعد بالبيع',
    r'\bcompromis\b':                 'عقد ابتدائي',
    r'\btransaction\b':               'صفقة عقارية',
    r'\bgarantie\b':                  'ضمان',
    r'\bvice caché\b':                'عيب خفي',
    r'\bpropriétaire\b':              'المالك',
    r'\blocataire\b':                 'المستأجر',
    r'\bbailleur\b':                  'المؤجر',
    r'\bloyer\b':                     'الإيجار',
    r'\bcopropriété\b':               'ملكية الطبقات',
    r'\bindivision\b':                'الشيوع',
    r'\busufruit\b':                  'حق الانتفاع',
    r'\bservitude\b':                 'حق الارتفاق',
    r'\bhypothèque\b':                'رهن',
    r'\bprescription\b':              'تقادم',
    r'\bpréemption\b':                'الشفعة',
    r'\bsaisie\b':                    'حجز',
    r'\bTVA\b':                       'أداء على القيمة المضافة',
    r'\bTIB\b':                       'ضريبة الأملاك المبنية',
    r'\bCPF\b':                       'رسم الصندوق العقاري',
    r'\bIRPP\b':                      'الضريبة على الدخل',
    r'\bdroits d\'enregistrement\b':  'معاليم التسجيل',
    r'\bdroit fixe\b':                'معلوم ثابت',
    r'\bexonération\b':               'إعفاء',
    r'\bplus-value\b':                'المكسب العقاري',
    r'\bregistre foncier\b':          'السجل العقاري',
    r'\bCOC\b':                       'مجلة الالتزامات والعقود',
    r'\bnon-hypothèque\b':            'شهادة عدم التحميل',
    r'\bnon-dette\b':                 'شهادة عدم المديونية',
    r'\btitre foncier\b':             'رسم عقاري',
    r'\bpermis de construire\b':      'رخصة البناء',
    r'\bcertificat de conformité\b':  'شهادة المطابقة',
    r'\blotissement\b':               'تقسيم أرض',
}


def _similar(a: str, b: str, threshold: float = 0.6) -> bool:
    if not a or not b:
        return False
    wa = set(a.split())
    wb = set(b.split())
    if not wa or not wb:
        return False
    return (len(wa & wb) / len(wa | wb)) >= threshold


def _apply_fr_to_ar_translations(text: str) -> str:
    sorted_patterns = sorted(_FR_TO_AR.keys(), key=len, reverse=True)
    for pattern in sorted_patterns:
        replacement = _FR_TO_AR[pattern]
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _clean_arabic_residues(text: str) -> str:
    # Only remove Latin words that are surrounded by Arabic characters (true residues),
    # NOT entire lines that may be fully in Latin (Gemini sometimes answers in French even
    # when the question is in Arabic — keep those lines rather than wiping the whole answer).
    text = re.sub(r'(?<=[؀-ۿ\s])\b[a-zA-Zéèêëàâùûüïîôœç]{4,}\b(?=[؀-ۿ\s])', '', text)
    text = re.sub(r'\*\*\s*\*\*', '', text)
    text = re.sub(r'\*\*\s*:\s*\*\*', '**', text)
    text = re.sub(r'\*\*\s*:\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[،,.:;/\-]+\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+([،,.:;])', r'\1', text)
    text = re.sub(r'\b(of the|of|the|and|or|in|at|to|for|with|by|from)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'  +', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def clean_response(text: str, lang: str) -> str:
    text = re.sub(
        r'\n(النقطة\s+(الأولى|الثانية|الثالثة|الرابعة|الخامسة|السادسة|السابعة))\s*\n',
        '\n', text
    )
    text = re.sub(r'\n[6-9]\.\s+', '\n', text)
    text = re.sub(r'\n1[0-9]\.\s+', '\n', text)

    if lang == "ar":
        text = _apply_fr_to_ar_translations(text)
        text = _clean_arabic_residues(text)

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

    seen_points: list[str] = []

    def dedup_point(m: re.Match) -> str:
        content = re.sub(r'\s+', ' ', m.group(2).strip().lower())
        if any(_similar(content, s) for s in seen_points):
            return ""
        seen_points.append(content)
        return m.group(0)

    text = re.sub(r'^(\d+\.\s+)(.+)$', dedup_point, text, flags=re.MULTILINE)

    counter = [0]

    def renumber(m: re.Match) -> str:
        counter[0] += 1
        return f"{counter[0]}. {m.group(2)}"

    text = re.sub(r'^(\d+\.\s+)(.+)$', renumber, text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)

    non_empty = [l for l in text.split("\n") if l.strip()]
    if len(non_empty) > 25:
        text = "\n".join(non_empty[:25])
        suffix = (
            "⚠️ للمزيد، استشر محامياً أو كاتب عدل."
            if lang == "ar"
            else "⚠️ Pour plus de détails, consultez un avocat ou notaire."
        )
        text += f"\n\n{suffix}"

    return text.strip()
