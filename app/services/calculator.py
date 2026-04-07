"""
app/services/calculator.py — Calculs financiers immobiliers
"""
import re


def is_calculation_question(question: str) -> bool:
    calc_kw = [
        "calculer", "calcul", "combien", "mensualité", "mensualite",
        "crédit", "prêt", "emprunt", "rendement", "rentabilité",
        "devis", "total", "payer", "coût", "cout",
        "تحسب", "احسب", "حساب", "قسط", "قرض", "مردودية", "عائد",
        "المجموع", "المبلغ الجملي",
    ]
    q = question.lower()

    has_amount = bool(re.search(r"\d{3,}", question))

    financial_kw = [
        "tva", "droit", "droits", "loyer", "taux", "prix", "valeur",
        "salaire", "notaire", "cpf", "promoteur", "appartement",
        "logement", "maison", "neuf", "ancien", "terrain",
    ]

    return any(k in q for k in calc_kw) or (has_amount and any(k in q for k in financial_kw))


def extract_numbers(text: str) -> list[float]:
    cleaned = re.sub(r"(\d)\s+(\d)", r"\1\2", text).replace(",", ".")
    result = []
    for n in re.findall(r"\b\d+\.?\d*\b", cleaned):
        try:
            v = float(n)
            if v > 0:
                result.append(v)
        except ValueError:
            pass
    return result


def _fmt_amount(v: float) -> str:
    return f"{v:,.0f}".replace(",", " ")


def _looks_like_new_promoter_purchase(q: str) -> bool:
    neuf_kw = ["neuf", "nouveau", "logement neuf", "appartement neuf", "maison neuve"]
    promoter_kw = ["promoteur", "promoteur immobilier", "promoteur agréé", "promoteur agree"]
    return any(k in q for k in neuf_kw) and any(k in q for k in promoter_kw)


def _wants_total(q: str) -> bool:
    total_kw = [
        "combien je dois payer", "combien payer", "payer en total", "payer au total",
        "total", "montant total", "devis total", "coût total", "cout total",
        "المبلغ الجملي", "المجموع", "total à payer",
    ]
    return any(k in q for k in total_kw)


def _price_is_ttc(q: str) -> bool:
    return "ttc" in q or "t.t.c" in q


def _price_is_ht(q: str) -> bool:
    return re.search(r"\bht\b", q) is not None


def _calc_new_apartment_total(price: float, q: str, lang: str) -> str:
    """
    Hypothèses par défaut utilisées ici :
    - achat d'un logement neuf auprès d'un promoteur
    - CPF = 1%
    - droit d'enregistrement du premier transfert = droit fixe
    - TVA :
        * 7% si prix <= 400 000 DT
        * 13% sinon
    - si l'utilisateur ne précise pas HT/TTC, on considère par défaut que le prix annoncé est HT
      pour éviter de sous-estimer le coût total.
    """
    AR = lang == "ar"

    # 1) Déterminer HT / TTC
    if _price_is_ttc(q):
        prix_ttc = price
        taux_tva = 7 if prix_ttc <= 400_000 else 13
        prix_ht = prix_ttc / (1 + taux_tva / 100)
        tva = prix_ttc - prix_ht
        mode_prix = "TTC"
    else:
        # HT par défaut si non précisé
        prix_ht = price
        taux_tva = 7 if prix_ht <= 400_000 else 13
        tva = prix_ht * taux_tva / 100
        prix_ttc = prix_ht + tva
        mode_prix = "HT (supposé)"

    # 2) Frais promoteur / premier transfert
    cpf = prix_ttc * 0.01

    # droit fixe d'enregistrement : on le laisse informatif car dépend souvent de l'acte / pages
    droit_fixe_info = "droit fixe d’enregistrement (non inclus car variable selon l’acte)"
    notaire_info = "frais de notaire non inclus (variables selon dossier)"

    total_hors_notaire = prix_ttc + cpf

    if AR:
        return (
            f"💰 **تقدير الكلفة الجملية لشراء شقة جديدة من باعث عقاري**\n\n"
            f"| البيان | القيمة |\n|---|---|\n"
            f"| السعر المدخل | **{_fmt_amount(price)} دت** |\n"
            f"| نوع السعر المعتمد | **{mode_prix}** |\n"
            f"| السعر HT | **{_fmt_amount(prix_ht)} دت** |\n"
            f"| نسبة TVA | **{taux_tva}%** |\n"
            f"| مبلغ TVA | **{_fmt_amount(tva)} دت** |\n"
            f"| السعر TTC | **{_fmt_amount(prix_ttc)} دت** |\n"
            f"| معلوم CPF (1%) | **{_fmt_amount(cpf)} دت** |\n"
            f"| **المجموع دون أتعاب العدل المنفذ/الموثق** | **{_fmt_amount(total_hors_notaire)} دت** |\n\n"
            f"ℹ️ {droit_fixe_info}.\n"
            f"ℹ️ {notaire_info}."
        )

    return (
        f"💰 **Devis total — appartement neuf chez promoteur**\n\n"
        f"| | |\n|---|---|\n"
        f"| Prix saisi | **{_fmt_amount(price)} DT** |\n"
        f"| Type de prix retenu | **{mode_prix}** |\n"
        f"| Prix HT | **{_fmt_amount(prix_ht)} DT** |\n"
        f"| TVA | **{taux_tva}%** |\n"
        f"| Montant TVA | **{_fmt_amount(tva)} DT** |\n"
        f"| Prix TTC | **{_fmt_amount(prix_ttc)} DT** |\n"
        f"| CPF 1% | **{_fmt_amount(cpf)} DT** |\n"
        f"| **Total hors notaire** | **{_fmt_amount(total_hors_notaire)} DT** |\n\n"
        f"ℹ️ {droit_fixe_info}.\n"
        f"ℹ️ {notaire_info}."
    )


def _calc_mensualite(principal: float, annual_rate: float, years: int) -> dict:
    r = annual_rate / 100 / 12
    n = years * 12
    m = principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1) if r else principal / n
    total = m * n
    return {
        "mensualite": round(m, 2),
        "total": round(total, 2),
        "interets": round(total - principal, 2),
    }


def handle_calculation(question: str, lang: str) -> str | None:
    q = re.sub(r"\s+", " ", question.lower()).strip()
    numbers = extract_numbers(question)
    AR = lang == "ar"

    montants = [n for n in numbers if n > 1000]

    # ── CAS PRIORITAIRE : logement neuf + promoteur + total ─────────────────
    if _looks_like_new_promoter_purchase(q) and _wants_total(q):
        if montants:
            prix = montants[0]
            return _calc_new_apartment_total(prix, q, lang)

    # ── TVA ──────────────────────────────────────────────────────────────────
    if any(k in q for k in ["tva", "ضريبة القيمة", "أداء على القيمة"]):
        if montants:
            prix = montants[0]
            taux = 7 if prix <= 400_000 else 13
            tva = prix * taux / 100
            ttc = prix + tva
            if AR:
                return (
                    f"💰 **حساب TVA — 2025**\n\n"
                    f"| البيان | القيمة |\n|---|---|\n"
                    f"| السعر HT | **{_fmt_amount(prix)} دت** |\n"
                    f"| نسبة TVA | **{taux}%** |\n"
                    f"| مبلغ TVA | **{_fmt_amount(tva)} دت** |\n"
                    f"| **السعر TTC** | **{_fmt_amount(ttc)} دت** |\n\n"
                    f"⚠️ تنطبق فقط على المساكن الجديدة من باعث مرخص."
                )
            return (
                f"💰 **Calcul TVA — 2025**\n\n"
                f"| | |\n|---|---|\n"
                f"| Prix HT | **{_fmt_amount(prix)} DT** |\n"
                f"| Taux TVA | **{taux}%** |\n"
                f"| Montant TVA | **{_fmt_amount(tva)} DT** |\n"
                f"| **Prix TTC** | **{_fmt_amount(ttc)} DT** |\n\n"
                f"⚠️ Logements neufs (promoteur agréé) uniquement."
            )

    # ── Droits d'enregistrement ancien / particulier ────────────────────────
    if any(k in q for k in ["enregistrement", "droits enregistr"]):
        if montants:
            prix = montants[0]
            if prix < 500_000:
                taux, label = 6, "< 500k"
            elif prix < 1_000_000:
                taux, label = 8, "500k–999k"
            else:
                taux, label = 10, "≥ 1M"
            droits = prix * taux / 100
            cpf = prix * 0.01
            total = droits + cpf
            if AR:
                return (
                    f"📋 **معاليم التسجيل**\n\n"
                    f"| البيان | القيمة |\n|---|---|\n"
                    f"| ثمن البيع | **{_fmt_amount(prix)} دت** |\n"
                    f"| نسبة التسجيل | **{taux}%** |\n"
                    f"| المعاليم | **{_fmt_amount(droits)} دت** |\n"
                    f"| رسم CPF 1% | **{_fmt_amount(cpf)} دت** |\n"
                    f"| **المجموع** | **{_fmt_amount(total)} دت** |"
                )
            return (
                f"📋 **Droits d'enregistrement**\n\n"
                f"| | |\n|---|---|\n"
                f"| Prix | **{_fmt_amount(prix)} DT** |\n"
                f"| Taux | **{taux}%** ({label}) |\n"
                f"| Droits | **{_fmt_amount(droits)} DT** |\n"
                f"| CPF 1% | **{_fmt_amount(cpf)} DT** |\n"
                f"| **Total** | **{_fmt_amount(total)} DT** |"
            )

    # ── Mensualité crédit ────────────────────────────────────────────────────
    if any(k in q for k in ["mensualité", "mensualite", "crédit", "prêt", "emprunt", "قسط", "قرض"]):
        large = sorted([n for n in numbers if n > 1000], reverse=True)
        if large:
            montant = large[0]
            taux = next((n for n in numbers if 0 < n < 25), 8.0)
            duree = int(next((n for n in numbers if 5 <= n <= 40), 20))
            r = _calc_mensualite(montant, taux, duree)
            if AR:
                return (
                    f"📊 **القسط الشهري**\n\n"
                    f"| البيان | القيمة |\n|---|---|\n"
                    f"| مبلغ القرض | **{_fmt_amount(montant)} دت** |\n"
                    f"| نسبة الفائدة | **{taux}%** |\n"
                    f"| المدة | **{duree} سنة** |\n"
                    f"| **القسط الشهري** | **{r['mensualite']:,.2f} دت** |\n"
                    f"| مجموع الفوائد | **{r['interets']:,.2f} دت** |\n"
                    f"| **المجموع الجملي** | **{r['total']:,.2f} دت** |"
                )
            return (
                f"📊 **Mensualité crédit**\n\n"
                f"| | |\n|---|---|\n"
                f"| Montant | **{_fmt_amount(montant)} DT** |\n"
                f"| Taux | **{taux}%** |\n"
                f"| Durée | **{duree} ans** |\n"
                f"| **Mensualité** | **{r['mensualite']:,.2f} DT** |\n"
                f"| Intérêts | **{r['interets']:,.2f} DT** |\n"
                f"| **Total** | **{r['total']:,.2f} DT** |"
            )

    # ── Rendement locatif ────────────────────────────────────────────────────
    if any(k in q for k in ["rendement", "rentabilité", "مردودية", "عائد"]):
        big = sorted([n for n in numbers if n > 500], reverse=True)
        if len(big) >= 2:
            val, loy = big[0], big[1]
            brut = round(loy * 12 / val * 100, 2)
            net = round((loy * 12 * 0.75) / val * 100, 2)
            if AR:
                return (
                    f"📈 **المردودية الإيجارية**\n\n"
                    f"| المؤشر | القيمة |\n|--------|--------|\n"
                    f"| قيمة العقار | **{_fmt_amount(val)} دت** |\n"
                    f"| الإيجار الشهري | **{_fmt_amount(loy)} دت** |\n"
                    f"| **مردودية خامة** | **{brut}%** |\n"
                    f"| **مردودية صافية** | **{net}%** |"
                )
            return (
                f"📈 **Rendement locatif**\n\n"
                f"| | |\n|---|---|\n"
                f"| Valeur | **{_fmt_amount(val)} DT** |\n"
                f"| Loyer mensuel | **{_fmt_amount(loy)} DT** |\n"
                f"| **Brut** | **{brut}%** |\n"
                f"| **Net** | **{net}%** |"
            )

    return None