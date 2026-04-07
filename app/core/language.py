"""
app/core/language.py — Détection langue + type de question
"""
import re


def detect_language(text: str) -> str:
    """Retourne 'ar' si le texte contient >15% de caractères arabes, sinon 'fr'."""
    arabic = len(re.findall(r'[\u0600-\u06FF]', text))
    return "ar" if arabic > len(text) * 0.15 else "fr"


def detect_question_type(question: str) -> str:
    """
    Classifie la question en catégorie juridique.
    Retourne une clé parmi :
      fiscal | legalite_bien | documents | expulsion | bailleur |
      plus_value | urbanisme | droits_reels | coc | chitchat | general
    """
    q = question.lower().strip()

    # ── Salutations / chitchat — réponse directe sans LLM juridique ──
    _chitchat_kw = [
        'bonjour', 'bonsoir', 'salut', 'hello', 'hi ', 'hey ',
        'merci', 'thank', 'شكرا', 'مرحبا', 'السلام', 'أهلا',
        'كيف حالك', 'comment ça va', 'ça va', 'بخير',
        'au revoir', 'bye', 'ok', 'okay', 'd\'accord',
    ]
    if any(q == kw.strip() or q.startswith(kw) for kw in _chitchat_kw):
        return "chitchat"

    # ── Fiscalité ────────────────────────────────────────────
    if any(k in q for k in [
        'tva', 'taxe', 'impôt', 'enregistrement', 'fiscal', 'tre', 'devises',
        'frais notaire', 'cpf',
        'ضريبة', 'أداء', 'تسجيل', 'جباية', 'اعفاء', 'معلوم',
    ]):
        return "fiscal"

    # ── Légalité bien ────────────────────────────────────────
    if any(k in q for k in [
        'légal', 'légalit', 'legal', 'legalit', 'vérifier', 'verifier',
        'vérification', 'contrôler', 'risque', 'arnaque', 'fiable',
        'libre de charge', 'hypothèque dessus', 'est légal', 'bien légal',
        'شرعية', 'قانونية', 'التحقق', 'فحص', 'تحقق من',
        'هل العقار', 'موثوق', 'عقار قانوني', 'صحة العقار',
    ]):
        return "legalite_bien"

    # ── Documents / acte ────────────────────────────────────
    if any(k in q for k in [
        'document', 'dossier', 'pièce', 'acte', 'notaire',
        'acheter', 'vendre', 'promesse', 'compromis',
        'وثيقة', 'ملف', 'بيع', 'شراء', 'كاتب عدل', 'وكالة',
    ]):
        return "documents"

    # ── Expulsion / bail / loyer ─────────────────────────────
    if any(k in q for k in [
        'expulsion', 'locataire', 'expulser', 'bail', 'loyer',
        'non-paiement', 'impayé', 'ne paie pas', 'paye pas',
        'résili', 'mettre dehors', 'mise en demeure',
        'طرد', 'مكتري', 'إخلاء', 'كراء', 'إيجار', 'فسخ',
        'لم يدفع', 'لا يدفع', 'عدم الدفع', 'المستأجر',
        'لم يسدد', 'ما دفعش', 'أشهر إيجار', 'أشهر كراء',
    ]):
        return "expulsion"

    # ── Obligations bailleur ─────────────────────────────────
    if any(k in q for k in [
        'obligation', 'bailleur', 'vice caché', 'réparation',
        'واجبات', 'التزامات المالك', 'عيب خفي', 'إصلاح',
    ]):
        return "bailleur"

    # ── Plus-value ───────────────────────────────────────────
    if any(k in q for k in [
        'plus-value', 'plus value', 'gain cession', 'irpp',
        'المكسب العقاري', 'ربح البيع', 'ضريبة البيع',
    ]):
        return "plus_value"

    # ── Urbanisme ────────────────────────────────────────────
    if any(k in q for k in [
        'permis', 'construire', 'construction', 'bâtir', 'bâtiment',
        'surélévation', 'extension', 'démolition', 'démolir',
        'urbanisme', 'aménagement', 'territoire', 'pau',
        "plan d'aménagement", 'plan urbain',
        'schéma directeur', 'zone', 'zonage', 'lotissement',
        'conformité', 'certificat de conformité',
        'cos', 'cuf', 'coefficient', 'hauteur', 'retrait',
        'littoral', 'domaine maritime', "étude d'impact",
        "servitude d'urbanisme", 'espace vert', 'voie publique',
        'bناء', 'ترخيص', 'تعمير', 'بلدية', 'مخطط', 'رخصة',
        'تهيئة', 'تقسيم', 'شهادة المطابقة', 'رخصة البناء',
        'منطقة سكنية', 'منطقة صناعية', 'مخالفة بناء',
    ]):
        return "urbanisme"

    # ── Droits réels ─────────────────────────────────────────
    if any(k in q for k in [
        'servitude', 'usufruit', 'copropriété', 'propriété',
        'droit réel', 'registre foncier', 'hypothèque',
        'prescription', 'préemption', 'indivision', 'partage',
        'succession', 'héritage', 'héritier',
        'حق عيني', 'ملكية', 'انتفاع', 'ارتفاق', 'مشاع',
        'رهن', 'حجز', 'السجل العقاري', 'الحقوق العينية',
        'شيوع', 'قسمة', 'تقادم', 'شفعة', 'ورثة',
        'ملكية الطبقات', 'نقابة المالكين',
    ]):
        return "droits_reels"

    # ── COC ──────────────────────────────────────────────────
    if any(k in q for k in [
        'contrat', 'nullité', 'dol', 'garantie', 'décennale',
        'عقد', 'بطلان', 'ضمان', 'التزام',
    ]):
        return "coc"

    return "general"
