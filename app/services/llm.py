"""
app/services/llm.py — Appel au LLM Ollama + post-traitement réponse

CORRECTIONS v3 :
- Dictionnaire fr→ar étendu (TIB, COC, CPF, TVA, registre foncier, etc.)
- Nettoyage des résidus après suppression : ** **, ponctuation orpheline,
  mots anglais (of, the, and...), espaces multiples
- Bugfixes regex conservés (groupes capturants dedup_point / renumber)
- Timeout réduit à 60s (était 120s)
"""
import re
from app.core.config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS

# ── Singleton LLM ──────────────────────────────────────────────────────────────

_llm_instance = None


def get_llm():
    """Retourne l'instance OllamaLLM (créée une seule fois)."""
    global _llm_instance
    if _llm_instance is None:
        from langchain_ollama import OllamaLLM
        _llm_instance = OllamaLLM(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            num_predict=LLM_MAX_TOKENS,
            timeout=60,                    # réduit de 120 → 60s
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


# ── Dictionnaire de traduction fr → ar ────────────────────────────────────────
# Couvre les termes juridiques tunisiens les plus fréquents

_FR_TO_AR: dict[str, str] = {
    # Acteurs juridiques
    r'\bhuissier\b':                  'محضر قضائي',
    r'\bnotaire\b':                   'كاتب عدل',
    r'\bjuge cantonal\b':             'قاضي الناحية',
    r'\bjuge\b':                      'قاضٍ',
    r'\bavocat\b':                    'محامٍ',
    r'\bpromoteur\b':                 'باعث عقاري',
    r'\bcréancier\b':                 'دائن',
    r'\bdébiteur\b':                  'مدين',
    r'\bhéritier\b':                  'وارث',
    # Procédures
    r'\bmise en demeure\b':           'إنذار رسمي',
    r'\baudience contradictoire\b':   'جلسة تناقضية',
    r'\bjugement\b':                  'حكم قضائي',
    r'\bsaisine\b':                   'إحالة',
    r'\bexpulsion\b':                 'طرد / إخلاء',
    r'\bexécution forcée\b':          'تنفيذ قسري',
    r'\bdélai légal\b':               'الأجل القانوني',
    r'\brecours\b':                   'طعن',
    r'\bappel\b':                     'استئناف',
    # Contrats et actes
    r'\bcontrat\b':                   'عقد',
    r'\bacte notarié\b':              'عقد رسمي',
    r'\bpromesse de vente\b':         'وعد بالبيع',
    r'\bcompromis\b':                 'عقد ابتدائي',
    r'\btransaction\b':               'صفقة عقارية',
    r'\bgarantie\b':                  'ضمان',
    r'\bvice caché\b':                'عيب خفي',
    # Biens et droits réels
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
    # Fiscalité et taxes
    r'\bTVA\b':                       'أداء على القيمة المضافة',
    r'\bTIB\b':                       'ضريبة الأملاك المبنية',
    r'\bCPF\b':                       'رسم الصندوق العقاري',
    r'\bIRPP\b':                      'الضريبة على الدخل',
    r'\bdroits d\'enregistrement\b':  'معاليم التسجيل',
    r'\bdroit fixe\b':                'معلوم ثابت',
    r'\bexonération\b':               'إعفاء',
    r'\bplus-value\b':                'المكسب العقاري',
    # Organismes et registres
    r'\bregistre foncier\b':          'السجل العقاري',
    r'\bCOC\b':                       'مجلة الالتزامات والعقود',
    r'\btableau cadastral\b':         'رسم مساحي',
    r'\bnon-opposition\b':            'عدم المعارضة',
    r'\bnon-hypothèque\b':            'شهادة عدم التحميل',
    r'\bnon-dette\b':                 'شهادة عدم المديونية',
    r'\btitre foncier\b':             'رسم عقاري',
    r'\bpermis de construire\b':      'رخصة البناء',
    r'\bcertificat de conformité\b':  'شهادة المطابقة',
    r'\blotissement\b':               'تقسيم أرض',
    # Divers
    r'\bassociated\b':                '',
    r'\bof the\b':                    '',
    r'\bof\b':                        '',
    r'\bthe\b':                       '',
    r'\band\b':                       '',
}


# ── Utilitaires ────────────────────────────────────────────────────────────────

def _similar(a: str, b: str, threshold: float = 0.6) -> bool:
    if not a or not b:
        return False
    wa = set(a.split())
    wb = set(b.split())
    if not wa or not wb:
        return False
    return (len(wa & wb) / len(wa | wb)) >= threshold


def _apply_fr_to_ar_translations(text: str) -> str:
    """Applique le dictionnaire de traduction fr→ar dans l'ordre décroissant de longueur."""
    # Trier par longueur décroissante pour éviter les remplacements partiels
    sorted_patterns = sorted(_FR_TO_AR.keys(), key=len, reverse=True)
    for pattern in sorted_patterns:
        replacement = _FR_TO_AR[pattern]
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _clean_arabic_residues(text: str) -> str:
    """
    Nettoie les résidus après suppression des mots français dans une réponse arabe.
    Ordre important : appliquer du plus spécifique au plus général.
    """
    # 1. Supprimer les mots latins résiduels (≥4 caractères)
    text = re.sub(r'\b[a-zA-Zéèêëàâùûüïîôœç]{4,}\b', '', text)

    # 2. Nettoyer les balises bold vides : ** ** ou **  **
    text = re.sub(r'\*\*\s*\*\*', '', text)

    # 3. Nettoyer "**: **texte" → "**texte"
    text = re.sub(r'\*\*\s*:\s*\*\*', '**', text)

    # 4. Nettoyer "** :" → supprimer complètement si rien après
    text = re.sub(r'\*\*\s*:\s*$', '', text, flags=re.MULTILINE)

    # 5. Nettoyer ponctuation orpheline en début/fin de ligne
    text = re.sub(r'^\s*[،,.:;/\-]+\s*$', '', text, flags=re.MULTILINE)

    # 6. Nettoyer espaces avant ponctuation arabe
    text = re.sub(r'\s+([،,.:;])', r'\1', text)

    # 7. Supprimer les mots anglais courts résiduels
    text = re.sub(r'\b(of the|of|the|and|or|in|at|to|for|with|by|from)\b', '', text, flags=re.IGNORECASE)

    # 8. Nettoyer espaces multiples et lignes vides doubles
    text = re.sub(r'  +', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text


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

    # 3. Traitement spécifique arabe
    if lang == "ar":
        # a) Traductions fr→ar
        text = _apply_fr_to_ar_translations(text)
        # b) Nettoyage des résidus
        text = _clean_arabic_residues(text)

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

    # 5. Dédupliquer les points numérotés
    seen_points: list[str] = []

    def dedup_point(m: re.Match) -> str:
        content = re.sub(r'\s+', ' ', m.group(2).strip().lower())
        if any(_similar(content, s) for s in seen_points):
            return ""
        seen_points.append(content)
        return m.group(0)

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
        suffix = (
            "⚠️ للمزيد، استشر محامياً أو كاتب عدل."
            if lang == "ar"
            else "⚠️ Pour plus de détails, consultez un avocat ou notaire."
        )
        text += f"\n\n{suffix}"

    return text.strip()