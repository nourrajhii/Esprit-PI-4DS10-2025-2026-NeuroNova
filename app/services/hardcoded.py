"""
app/services/hardcoded.py — Règles juridiques hardcodées + registre des sources
Ces règles couvrent les sujets les plus fréquents sans nécessiter FAISS.
"""

# ── Règles hardcodées ─────────────────────────────────────────────────────────

FISCAL_RULES = """
=== FISCALITÉ IMMOBILIÈRE TUNISIE 2025 (LOI DE FINANCES N°48-2024) ===

TVA LOGEMENT NEUF (promoteur agréé) :
- Prix ≤ 400 000 DT → TVA 7%
- Prix > 400 000 DT → TVA 13%
- PAS de TVA sur reventes entre particuliers (bien ancien)

DROITS D'ENREGISTREMENT (bien ancien / entre particuliers) :
- Prix < 500 000 DT    → 6%
- Prix 500k–999 999 DT → 8%
- Prix ≥ 1 000 000 DT  → 10%
- Taxe CPF : +1% sur tout achat | Frais notaire : 1% à 5% du prix

TRE (paiement 100% devises) :
- CPF 1% uniquement + droit fixe 30 DT/page

IS PROMOTEURS :
- Taux général : 20% | Logements sociaux : exo 50%

REVENUS LOCATIFS :
- Déduction forfaitaire : 25% du loyer brut (LF2025)

TAUX BANCAIRES :
- BCT : 8% | Marché : 8%-11% | FOPROLOS : ≤ 2% (salaire ≤ 3 162 DT/mois)
"""

DOCUMENTS_VENTE = """
=== DOCUMENTS VENTE IMMOBILIÈRE TUNISIE ===

VENDEUR : CIN | Titre foncier original | Cert. matrimoniale
| Cert. non-opposition/non-hypothèque | Quittances TIB | Attestation non-dette fiscale

BIEN : Titre foncier INDISPENSABLE | Plan cadastral | Permis construire
| PV réception travaux | Règlement copropriété si appartement

HÉRITIERS : Acte dévolution successorale | Accord TOUS héritiers

PROCÉDURE : (1) Docs → (2) Acte notaire → (3) Droits enregistrement
→ (4) Bureau Propriété Foncière → (5) Nouveau titre (2-8 semaines)
"""

DROITS_EXPULSION = """
=== PROCÉDURE NON-PAIEMENT LOYER / EXPULSION TUNISIE ===

PRINCIPE FONDAMENTAL : Aucune expulsion sans décision judiciaire.

ÉTAPES :
1. Mise en demeure écrite par huissier (عدل منفذ) — obligatoire
2. Délai légal : 2 mois minimum
3. Sans paiement → saisine du juge cantonal (محكمة الناحية)
4. Audience contradictoire
5. Jugement → signification par huissier
6. Délai d'exécution : 1 à 3 mois
7. Exécution uniquement par huissier

BASE LÉGALE : Articles 726 à 798 COC
"""

OBLIGATIONS_BAILLEUR = """
=== OBLIGATIONS DU BAILLEUR — COC TUNISIE ===

OBLIGATIONS (art. 726-727 COC) :
1. Délivrance en bon état
2. Garantie de jouissance paisible
3. Grosses réparations à sa charge

RÉPARATIONS :
- Grosses (structure, toiture) → PROPRIÉTAIRE
- Locatives courantes → LOCATAIRE
- Vétusté normale → PROPRIÉTAIRE
"""

PLUS_VALUE_IMMO = """
=== PLUS-VALUE IMMOBILIÈRE TUNISIE ===

CALCUL (art. 27 Code IRPP/IS) :
Plus-value = Prix cession − (Prix achat × (1 + 10% × années détention))
- Cession ≤ 5 ans : impôt 15%
- Cession > 5 ans : impôt 10%
- Héritage : 10%
- Déclaration : 3 mois après cession
"""

URBANISME_RULES = """
=== CODE AMÉNAGEMENT / URBANISME — LOI N°94-122 DU 28/11/1994 ===

PERMIS DE CONSTRUIRE :
- Obligatoire pour toute construction, extension, surélévation
- Délai instruction : 2-3 mois | Validité : 3 ans
- Sans permis : amende + ordre de démolition

LITTORAL : Interdit de construire à moins de 100 m du domaine public maritime

COEFFICIENTS :
- COS (surface plancher / surface terrain)
- CUF (surface bâtie / surface terrain)
- Hauteur max, retrait façade 3-5m, retrait latéral 1.5-3m selon zone

CERTIFICAT DE CONFORMITÉ : obligatoire avant occupation
"""

COC_RULES = """
=== CODE DES OBLIGATIONS ET CONTRATS (COC) — IMMOBILIER ===

VENTE (art. 580+) :
- Parfaite par accord sur la chose et le prix
- Garantie : possession paisible + absence de vices cachés

BAIL (art. 726-798) :
- Sous-location interdite sans accord écrit (art. 763)
- Rétractation vendeur : exécution forcée ou dommages
- Rétractation acheteur : perd l'acompte (max 10%)

RESPONSABILITÉ DÉCENNALE (art. 114) :
- Entrepreneur + architecte responsables 10 ans des défauts graves
"""

DROITS_REELS_RULES = """
=== CODE DES DROITS RÉELS — RÉSUMÉ ===

Propriété (art. 17-21) : droit absolu | expropriation → indemnité juste
Prescription : 15 ans non immatriculé | 10 ans bonne foi | ZÉRO immatriculé
Indivision (art. 56-71) : 3/4 valeur pour décisions | partage imprescriptible
Copropriété (art. 85-102) : syndicat obligatoire | charges proportionnelles
Préemption (art. 103-115) : 1 mois notifié / 6 mois inscription
Hypothèque (art. 270-302) : naissance à inscription | suit l'immeuble
Registre foncier (art. 303-405) : droit non inscrit = nul
"""

LEGALITE_BIEN_RULES = """
=== COMMENT VÉRIFIER LA LÉGALITÉ D'UN BIEN IMMOBILIER EN TUNISIE ===

ÉTAPE 1 — TITRE FONCIER : Obtenir l'original + attestation < 3 mois
ÉTAPE 2 — HYPOTHÈQUES : Certificat de non-hypothèque (شهادة عدم تحميل)
ÉTAPE 3 — URBANISME : Permis de construire + certificat de conformité
ÉTAPE 4 — FISCAL : Quittances TIB à jour + attestation non-dette fiscale
ÉTAPE 5 — LITIGES : Absence de قيد احتياطي au registre foncier

PRINCIPE (art. 305 مجلة الحقوق العينية) :
Tout droit réel ne prend naissance qu'à son inscription au registre foncier.
"""

# ── Mapping type → (contexte hardcodé, source label) ─────────────────────────

HARDCODED_RULES: dict[str, str] = {
    "fiscal":        FISCAL_RULES,
    "documents":     DOCUMENTS_VENTE,
    "expulsion":     DROITS_EXPULSION,
    "bailleur":      OBLIGATIONS_BAILLEUR,
    "plus_value":    PLUS_VALUE_IMMO,
    "urbanisme":     URBANISME_RULES,
    "coc":           COC_RULES,
    "droits_reels":  DROITS_REELS_RULES,
    "legalite_bien": LEGALITE_BIEN_RULES,
}

HARDCODED_SOURCE_LABELS: dict[str, tuple[str, str]] = {
    "fiscal":        ("💰", "Loi de Finances 2025 (n°48-2024)"),
    "documents":     ("📋", "Procédure notariale / Propriété foncière"),
    "expulsion":     ("⚖️",  "COC art. 726-798 — Bail / Expulsion"),
    "bailleur":      ("📜", "Code des Obligations et Contrats (COC)"),
    "plus_value":    ("📈", "Code IRPP/IS — Art. 27"),
    "urbanisme":     ("🏙️", "Code de l'Aménagement du Territoire — Loi N°94-122"),
    "coc":           ("📜", "Code des Obligations et Contrats (COC)"),
    "droits_reels":  ("🏛️", "مجلة الحقوق العينية — Code des Droits Réels"),
    "legalite_bien": ("🔍", "مجلة الحقوق العينية + Code Urbanisme"),
    "general":       ("📚", "Base juridique générale"),
}

# ── Registre des noms de fichiers sources ─────────────────────────────────────

SOURCE_REGISTRY: dict[str, dict] = {
    "loi.txt": {
        "icon": "🏛️",
        "label": "مجلة الحقوق العينية — Code des Droits Réels (bilingue)",
        "short": "مجلة الحقوق العينية",
    },
    "droit_reel.txt": {
        "icon": "🏛️",
        "label": "Code des Droits Réels — Loi n°5/1965 + Loi 17/1990",
        "short": "CDR 1965 / Loi 17-1990",
    },
    "COC.pdf": {
        "icon": "📜",
        "label": "Code des Obligations et Contrats (COC)",
        "short": "COC",
    },
    "urbanisme.pdf": {
        "icon": "🏙️",
        "label": "Code de l'Aménagement du Territoire — Loi N°94-122",
        "short": "Code Urbanisme",
    },
    "loi_location.txt": {
        "icon": "🏛️",
        "label": "Loi sur la location immobilière",
        "short": "Loi Location",
    },
}
