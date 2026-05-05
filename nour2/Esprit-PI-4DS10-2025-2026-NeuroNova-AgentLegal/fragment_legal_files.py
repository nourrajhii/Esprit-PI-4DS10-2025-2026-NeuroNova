"""
fragment_legal_files.py
=======================
Fragmente intelligemment les fichiers juridiques tunisiens en sous-fichiers
thématiques prêts à être indexés dans FAISS.

Structure de sortie :
    data/
    ├── droit_reel/
    │   ├── 01_generalites_biens.txt
    │   ├── 02_propriete.txt
    │   ├── 03_prescription_indivision.txt
    │   ├── 04_usufruit_servitudes.txt
    │   ├── 05_hypotheque_privileges.txt
    │   └── 06_enregistrement_foncier.txt
    ├── loi/
    │   ├── 01_generalites_biens.txt
    │   ├── 02_propriete_prescription.txt
    │   ├── 03_indivision_copropriete.txt
    │   ├── 04_usufruit_servitudes.txt
    │   ├── 05_hypotheque_registre.txt
    │   └── 06_droits_reels_divers.txt
    └── loi_location/
        ├── 01_generalites_propriete.txt
        ├── 02_prescription_indivision.txt
        ├── 03_promotion_immobiliere.txt
        └── 04_obligations_promoteur.txt
"""

import os
import re
from pathlib import Path

OUTPUT_DIR = Path("data")


# ─────────────────────────────────────────────────────────────────────────────
# UTILITAIRES
# ─────────────────────────────────────────────────────────────────────────────

def read_file(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def write_fragment(lines: list[str], output_path: Path, label: str):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines).strip()
    if not content:
        print(f"  ⚠️  Fragment vide ignoré : {output_path.name}")
        return
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content + "\n")
    char_count = len(content)
    print(f"  ✅  {output_path.name:45s} — {char_count:6,} chars  ({label})")


def is_separator(line: str) -> bool:
    return bool(re.match(r'^={10,}', line.strip()))


def find_line(lines: list[str], pattern: str) -> int:
    """Retourne l'index de la première ligne correspondant au pattern."""
    for i, line in enumerate(lines):
        if re.search(pattern, line):
            return i
    return -1


def find_all_lines(lines: list[str], pattern: str) -> list[int]:
    return [i for i, line in enumerate(lines) if re.search(pattern, line)]


def extract_range(lines: list[str], start: int, end: int) -> list[str]:
    """Extrait et nettoie un bloc de lignes."""
    chunk = lines[start:end]
    # Supprimer les lignes vides en début et fin
    while chunk and not chunk[0].strip():
        chunk.pop(0)
    while chunk and not chunk[-1].strip():
        chunk.pop()
    return chunk


# ─────────────────────────────────────────────────────────────────────────────
# DROIT_REEL.TXT — 498 lignes
# Structure : LIVRE I (Titres I-VI) + LIVRE II (Enregistrement foncier)
# ─────────────────────────────────────────────────────────────────────────────

def fragment_droit_reel(src: str):
    print("\n📂 droit_reel.txt")
    lines = read_file(src)
    out = OUTPUT_DIR / "droit_reel"

    # Repères par pattern
    def find(pattern): return find_line(lines, pattern)

    # Titre I — Généralités / Biens (début → Titre II Propriété)
    t1_start = 0
    t2_start = find(r'العنوان الثاني.*حق الملكية|TITRE II.*PROPRI')
    t3_start = find(r'العنوان الثالث.*انتفاع|TITRE III.*USUFRUIT')
    t4_start = find(r'العنوان الرابع.*ارتفاق|TITRE IV.*SERVITUDE')
    t5_start = find(r'العنوان الخامس.*رهن|TITRE V.*HYPOTH')
    t6_start = find(r'العنوان السادس.*امتياز|TITRE VI.*PRIVIL')
    livre2_start = find(r'الكتاب الثاني.*تسجيل|LIVRE SECOND.*ENREGISTREMENT')
    end = len(lines)

    fragments = [
        ("01_generalites_biens.txt",       t1_start,    t2_start,    "Généralités + Biens"),
        ("02_propriete.txt",               t2_start,    t3_start,    "Droit de propriété"),
        ("03_usufruit_usage.txt",          t3_start,    t4_start,    "Usufruit / Usage / Habitation"),
        ("04_servitudes.txt",              t4_start,    t5_start,    "Servitudes"),
        ("05_hypotheque_privileges.txt",   t5_start,    livre2_start, "Hypothèque + Privilèges"),
        ("06_enregistrement_foncier.txt",  livre2_start, end,         "Enregistrement foncier"),
    ]

    for fname, s, e, label in fragments:
        if s < 0:
            print(f"  ⚠️  Repère non trouvé pour {fname}")
            continue
        write_fragment(extract_range(lines, s, e), out / fname, label)


# ─────────────────────────────────────────────────────────────────────────────
# LOI.TXT — 616 lignes
# Structure bilingue : LIVRE I (Titres I-VII+) — plus riche que droit_reel
# ─────────────────────────────────────────────────────────────────────────────

def fragment_loi(src: str):
    print("\n📂 loi.txt")
    lines = read_file(src)
    out = OUTPUT_DIR / "loi"

    def find(pattern): return find_line(lines, pattern)

    # Repères structurels
    t1_start   = 0
    t2_start   = find(r'TITRE II.*IMMEUBLE|العنوان.*الثاني.*عقار')
    t3_start   = find(r'TITRE III.*MEUBLE|العنوان.*الثالث.*منقول')
    t4_start   = find(r'TITRE IV.*PROPRI|العنوان.*الرابع.*ملكية')
    t5_start   = find(r'TITRE V.*INDIVIS|العنوان.*الخامس.*شيوع')
    t6_start   = find(r'TITRE VI.*COPRO|العنوان.*السادس.*طبقات|ملكية الطبقات')
    t7_start   = find(r'TITRE VII.*PREEMP|العنوان.*السابع.*شفعة|الشفعة')
    t8_start   = find(r'TITRE VIII.*USUFRUI|العنوان.*الثامن.*انتفاع')
    t9_start   = find(r'TITRE IX.*SERVI|العنوان.*التاسع.*ارتفاق')
    t10_start  = find(r'TITRE X.*HYPOTH|العنوان.*العاشر.*رهن')
    registre   = find(r'REGISTRE.*FONC|السجل.*العقاري|الكتاب الثاني')
    end = len(lines)

    # Construction dynamique : ignorer les repères -1
    checkpoints = sorted(
        [(i, n, l) for i, n, l in [
            (t1_start,  "01_definition_biens.txt",       "Définition des biens"),
            (t2_start,  "02_immeubles.txt",               "Les immeubles"),
            (t3_start,  "03_meubles.txt",                 "Les meubles"),
            (t4_start,  "04_propriete_prescription.txt",  "Propriété + Prescription"),
            (t5_start,  "05_indivision.txt",              "Indivision (Shiyou3)"),
            (t6_start,  "06_copropriete_batiments.txt",   "Copropriété / Batiments"),
            (t7_start,  "07_preemption.txt",              "Préemption (Chof3a)"),
            (t8_start,  "08_usufruit_usage.txt",          "Usufruit / Usage"),
            (t9_start,  "09_servitudes.txt",              "Servitudes"),
            (t10_start, "10_hypotheque.txt",              "Hypothèque"),
            (registre,  "11_registre_foncier.txt",        "Registre foncier"),
        ] if i >= 0]
    )

    for idx, (start, fname, label) in enumerate(checkpoints):
        end_pos = checkpoints[idx + 1][0] if idx + 1 < len(checkpoints) else end
        write_fragment(extract_range(lines, start, end_pos), out / fname, label)


# ─────────────────────────────────────────────────────────────────────────────
# LOI_LOCATION.TXT — 486 lignes
# Structure : CDR (loi 1965) partiel + Loi 17/1990 (promotion immobilière)
# ─────────────────────────────────────────────────────────────────────────────

def fragment_loi_location(src: str):
    print("\n📂 loi_location.txt")
    lines = read_file(src)
    out = OUTPUT_DIR / "loi_location"

    def find(pattern): return find_line(lines, pattern)

    # Partie 1 : CDR 1965 — Généralités + Biens
    cdr_start      = 0
    propriete      = find(r'العنوان الثاني.*ملكية|TITRE II.*PROPRI')
    acq_propriete  = find(r'الجزء الأول.*اكتساب|أسباب اكتساب')
    indivision     = find(r'الجزء الثاني.*شيوع|INDIVIS')

    # Partie 2 : Loi 17/1990 — Promotion immobilière
    loi17_start    = find(r'قانون عدد 17 لسنة 1990|LOI N°17.*1990|PROMOTION IMMOBILI')
    titre1_loi17   = find(r'العنوان الأول.*أحكام عامة')
    titre2_loi17   = find(r'العنوان الثاني.*الترخيص|AUTORISATION|AGRÉ')
    titre3_loi17   = find(r'العنوان الثالث.*واجبات|OBLIGATION')
    titre4_loi17   = find(r'الباب الرابع.*تشجيعات|الباب الرابع.*امتياز|AVANTAGE|INCITATION')
    end = len(lines)

    checkpoints = sorted(
        [(i, n, l) for i, n, l in [
            (cdr_start,     "01_cdr_generalites_biens.txt",         "CDR — Généralités + Biens"),
            (propriete,     "02_cdr_propriete.txt",                 "CDR — Droit de propriété"),
            (acq_propriete, "03_cdr_acquisition_prescription.txt",  "CDR — Acquisition + Prescription"),
            (indivision,    "04_cdr_indivision.txt",                "CDR — Indivision"),
            (loi17_start,   "05_loi17_generalites.txt",             "Loi 17/1990 — Généralités"),
            (titre2_loi17,  "06_loi17_agrement_autorisation.txt",   "Loi 17/1990 — Agrément/Autorisation"),
            (titre3_loi17,  "07_loi17_obligations_promoteur.txt",   "Loi 17/1990 — Obligations promoteur"),
            (titre4_loi17,  "08_loi17_avantages_fiscaux.txt",       "Loi 17/1990 — Avantages fiscaux"),
        ] if i >= 0]
    )

    for idx, (start, fname, label) in enumerate(checkpoints):
        end_pos = checkpoints[idx + 1][0] if idx + 1 < len(checkpoints) else end
        write_fragment(extract_range(lines, start, end_pos), out / fname, label)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("✂️  Fragmentation des fichiers juridiques tunisiens")
    print("=" * 60)

    sources = {
        "droit_reel.txt":   (fragment_droit_reel,    "/home/claude/droit_reel.txt"),
        "loi.txt":          (fragment_loi,           "/home/claude/loi.txt"),
        "loi_location.txt": (fragment_loi_location,  "/home/claude/loi_location.txt"),
    }

    total_files = 0
    for name, (fn, path) in sources.items():
        if not Path(path).exists():
            print(f"\n⚠️  Fichier non trouvé : {path}")
            continue
        fn(path)
        created = list((OUTPUT_DIR / name.replace(".txt", "")).glob("*.txt"))
        total_files += len(created)

    print("\n" + "=" * 60)
    print(f"✅  {total_files} fichiers fragments créés dans ./data/")
    print("=" * 60)
    print("\n📋 Structure finale :")
    for folder in sorted(OUTPUT_DIR.iterdir()):
        if folder.is_dir():
            files = sorted(folder.glob("*.txt"))
            print(f"\n  📁 {folder.name}/")
            for f in files:
                size = f.stat().st_size
                print(f"     {f.name:45s} {size:6,} bytes")

    print("\n🚀 Prochaine étape : python build_db.py")


if __name__ == "__main__":
    main()
