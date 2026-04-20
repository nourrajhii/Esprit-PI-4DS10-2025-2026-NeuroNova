"""
ConstructionAgent v6.0
─────────────────────────────────────────────────────────────────────────────
Corrections v6.0 :
  - BUG FIX #1 : nombre_etages correctement calculé pour "2 niveaux" / "2 étages"
    → "2 étages" = 2 niveaux (RDC + 1er), PAS 3.
    → "2 appartements aux étages" = 3 niveaux (RDC + 2 étages).
  - BUG FIX #2 : _validate_type_projet détecte mieux mixte_maison_appart
    quand le message dit "2 niveaux / le 1er étage ... le 2ème étage ..."
  - BUG FIX #3 : pièces PAR appartement bien isolées — pas de multiplication
    sur le total déjà additionné par l'utilisateur.
  - BUG FIX #4 : EXTRACT_PROMPT clarifie que nombre_etages = nombre de
    NIVEAUX TOTAL (RDC = niveau 1 et comptabilisé).
─────────────────────────────────────────────────────────────────────────────
"""

import re
import json
from typing import Optional

import ollama

from .rag_retriever import RAGRetriever
from .devis_calculator import DevisCalculator


# ── Prompt système ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Tu es un expert en construction, rénovation ET immobilier en Tunisie.
Tu aides les clients à :
1. Obtenir une estimation du coût de leur projet de construction/rénovation.
2. Trouver le meilleur bien immobilier à acheter selon leur budget et leurs critères.

Règles importantes :
- Ne jamais inventer de prix ou de données
- Les prix viennent exclusivement du dataset de marché tunisien 2025
- Toujours répondre en français
- Pour les devis : inclure fourchette MIN / MOY / MAX
- Pour l'immobilier : comparer et recommander le meilleur investissement
"""

EXTRACT_PROMPT = """À partir du message suivant, extrais les informations du projet de construction.

Message : {message}

Réponds UNIQUEMENT avec un objet JSON valide, sans texte autour, sans balises markdown.
Format exact :
{{
  "terrain_m2": <nombre ou null>,
  "nombre_etages": <NOMBRE TOTAL DE NIVEAUX — RDC = niveau 1.
    Exemples :
    "1 étage" ou "un étage" → 2 (RDC + 1er étage)
    "2 étages" → 3 (RDC + 2 étages)
    "2 niveaux" → 2
    "3 niveaux" → 3
    "le 1er étage ... le 2ème étage" (2 appartements) → 3 (RDC + 2 niveaux d'apparts)
    "café RDC + 2 appartements en haut" → 3
    "5 étages" → 6 (RDC + 5)
    "duplex" → 2
    "plain-pied / RDC seul" → 1>,
  "type_projet": "<construction|renovation|cafe_commerce|appartement|villa|hotel|foyer|centre_esthetique|salle_sport|clinique|bureau|salle_fetes|entrepot|mixte_cafe_appart|mixte_maison_appart>",
  "nb_appartements": <nombre d'appartements indépendants si projet multi-logements, sinon null>,
  "pieces": {{
    "chambres": <TOTAL réel sur TOUS les appartements/niveaux — additionner chaque appart.
      Ex: "appart 1 : 2 chambres, appart 2 : 3 chambres" → 5>,
    "salons": <total — ex "2 apparts avec 1 salon chacun" → 2>,
    "cuisines": <total — ex "2 apparts avec 1 cuisine chacun" → 2>,
    "salles_de_bain": <total — ex "appart1: 2 SDB, appart2: 3 SDB" → 5>,
    "wc": <nombre total>,
    "jardin": <true|false>,
    "piscine": <true|false>,
    "dressing": <true|false>
  }},
  "qualite": "<economique|standard|premium>",
  "infos_suffisantes": <true|false>
}}

RÈGLES IMPORTANTES :
- type_projet "mixte_maison_appart" si maison/logement au RDC ET appartements aux étages (sans café).
  Ex: "le 1er étage une maison ... le 2ème étage un appartement" → mixte_maison_appart, nb_appartements=1, nombre_etages=2.
  Ex: "2 niveaux : niveau 1 = logement 2 ch, niveau 2 = logement 3 ch" → mixte_maison_appart, nb_appartements=1, nombre_etages=2.
- type_projet "mixte_cafe_appart" UNIQUEMENT si café/commerce explicite au RDC.
- nombre_etages : COMPTER les niveaux occupés. "2 niveaux" = 2. "le 1er et le 2ème étage" = 2 niveaux d'apparts + RDC = 3 total.
- nb_appartements : nombre de logements indépendants (hors RDC si c'est une maison).
  Pour "2 niveaux chacun un appartement" → nb_appartements=2, nombre_etages=2 (pas de RDC séparé).
  Pour "maison RDC + 2 étages" → nb_appartements=2, nombre_etages=3.
- chambres/salons/cuisines/SDB : TOUJOURS le TOTAL. Additionner CHAQUE appartement séparément.
- jardin/piscine/dressing : true si mentionné.
- infos_suffisantes = true si terrain_m2 présent ET au moins une pièce ou type commercial.
"""


# ── Prompt extraction critères immobiliers ─────────────────────────────────────

IMMO_EXTRACT_PROMPT = """À partir du message suivant, extrais les critères de recherche immobilière.

Message : {message}

Réponds UNIQUEMENT avec un objet JSON valide, sans texte autour, sans balises markdown.
Format exact :
{{
  "ville": "<nom de la ville ou null>",
  "budget_max": <budget maximum en DT (nombre entier) ou null>,
  "budget_min": <budget minimum en DT ou null>,
  "type_bien": "<appartement|villa|maison|terrain|commerce ou null>",
  "surface_min": <surface minimum en m² ou null>,
  "rooms_min": <nombre minimum de pièces/chambres ou null>
}}

Exemples de conversion budget :
- "300 mille DT" → 300000
- "500k" → 500000
- "1 million" → 1000000
- "300 000 DT" → 300000

Règles :
- Si la ville n'est pas mentionnée, mettre null
- Si le type n'est pas mentionnable clairement, mettre null
- Pour le budget, prendre le montant maximum si une fourchette est donnée
"""


# ── Mots-clés pour détecter l'intention immobilière ──────────────────────────

IMMO_KEYWORDS = [
    "acheter", "achat", "acquérir", "acquis",
    "investir", "investissement",
    "cherche un", "cherche une",
    "trouver un appartement", "trouver une maison", "trouver une villa",
    "à vendre", "a vendre", "disponible",
    "budget de", "budget max",
    "quel bien", "quel appartement", "quelle villa",
    "recommande", "recommandez",
    "comparer", "comparaison",
    "meilleur prix", "bon prix", "moins cher",
    "immobilier", "propriété", "annonce",
    "je veux acheter", "je veux investir",
    "un appartement", "une maison", "une villa", "un terrain",
]

# ── Normalisation des types de projet ────────────────────────────────────────

_TYPE_NORM = {
    "construction": "construction", "maison": "construction",
    "house": "construction", "neuf": "construction", "neuve": "construction",
    "villa": "villa", "duplex": "villa",
    "renovation": "renovation", "rénovation": "renovation", "renov": "renovation",
    "cafe_commerce": "cafe_commerce", "cafe": "cafe_commerce",
    "commerce": "cafe_commerce", "restaurant": "cafe_commerce",
    "appartement": "appartement", "appart": "appartement", "studio": "appartement",
    "mixte_cafe_appart": "mixte_cafe_appart",
    "mixte_maison_appart": "mixte_maison_appart",
    "hotel": "hotel", "hôtel": "hotel",
    "foyer": "foyer",
    "centre_esthetique": "centre_esthetique", "esthetique": "centre_esthetique",
    "spa": "centre_esthetique", "hammam": "centre_esthetique",
    "salle_sport": "salle_sport", "gym": "salle_sport", "fitness": "salle_sport",
    "clinique": "clinique", "cabinet": "clinique", "pharmacie": "clinique",
    "bureau": "bureau", "bureaux": "bureau", "coworking": "bureau",
    "salle_fetes": "salle_fetes", "salle fetes": "salle_fetes",
    "entrepot": "entrepot", "entrepôt": "entrepot", "hangar": "entrepot",
}


class ConstructionAgent:

    def __init__(self,
                 retriever: RAGRetriever,
                 calculator: DevisCalculator,
                 model: str = "llama3.2:1b",
                 listings_path: str = "data/ai_ready_listings.csv"):
        self.retriever  = retriever
        self.calculator = calculator
        self.model      = model
        self.history    = []

    # ── Entrée principale ──────────────────────────────────────────────────────

    def chat(self, message: str) -> dict:
        self.history.append({"role": "user", "content": message})
        intention = self._detect_intention(message)
        if intention == "immobilier":
            return self._handle_immo(message)
        else:
            return self._handle_devis(message)

    # ── Détection d'intention ─────────────────────────────────────────────────

    def _detect_intention(self, message: str) -> str:
        txt = message.lower()
        immo_score = sum(1 for kw in IMMO_KEYWORDS if kw in txt)
        devis_keywords = [
            "terrain de", "construire", "construction", "rénover", "rénovation",
            "devis", "coût", "cout", "combien ça coûte", "prix construction",
            "m²", "m2", "chambres à construire", "bâtir",
            "hôtel", "hotel", "foyer", "esthétique", "esthetique",
            "salle de sport", "gym", "clinique", "bureau", "salle des fêtes",
            "entrepôt", "entrepot",
        ]
        devis_score = sum(1 for kw in devis_keywords if kw in txt)

        if re.search(r"\d+\s*m[²2]", txt) and any(
            k in txt for k in ["construire", "terrain", "bâtir", "construction",
                                "hôtel", "foyer", "esthétique", "salle de sport"]
        ):
            return "devis"

        if immo_score >= 2:
            return "immobilier"

        strong_immo = [
            "acheter", "achat", "investir", "à vendre",
            "je veux un appartement", "je veux une maison", "je veux une villa",
        ]
        if any(kw in txt for kw in strong_immo) and devis_score == 0:
            return "immobilier"

        return "devis"

    # ════════════════════════════════════════════════════════════════════════════
    # BRANCHE IMMOBILIER
    # ════════════════════════════════════════════════════════════════════════════

    def _handle_immo(self, message: str) -> dict:
        if not hasattr(self, "recommender") or self.recommender is None:
            reponse = (
                "❌ Le module de recommandation immobilière n'est pas disponible.\n"
                "Vérifiez que le fichier `data/ai_ready_listings.csv` est présent."
            )
            self.history.append({"role": "assistant", "content": reponse})
            return {"texte": reponse, "devis": None, "properties": None}

        criteres = self._extract_immo_criteria(message)
        result = self.recommender.recommend(
            city=criteres.get("ville"),
            budget_max=criteres.get("budget_max"),
            budget_min=criteres.get("budget_min"),
            type_bien=criteres.get("type_bien"),
            surface_min=criteres.get("surface_min"),
            rooms_min=criteres.get("rooms_min"),
            top_n=5,
        )
        texte = self.recommender.format_recommendation(result, criteres)
        self.history.append({"role": "assistant", "content": texte})
        return {"texte": texte, "devis": None, "properties": result}

    def _extract_immo_criteria(self, message: str) -> dict:
        prompt = IMMO_EXTRACT_PROMPT.format(message=message)
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1, "num_predict": 300},
            )
            raw = response["message"]["content"].strip()
            raw = re.sub(r"```(?:json)?", "", raw).strip("` \n")
            return json.loads(raw)
        except Exception:
            return self._extract_immo_regex(message)

    def _extract_immo_regex(self, message: str) -> dict:
        txt = message.lower()
        budget_max = None
        m = re.search(r"(\d[\d\s]*)\s*(?:mille|k\b|000)", txt)
        if m:
            raw_num = float(re.sub(r"\s", "", m.group(1)))
            budget_max = raw_num * 1000 if raw_num < 10_000 else raw_num
        else:
            m2 = re.search(r"(\d[\d\s]{4,})", txt)
            if m2:
                budget_max = float(re.sub(r"\s", "", m2.group(1)))

        type_bien = None
        if any(k in txt for k in ["appartement", "appart", "s+1", "s+2", "s+3"]):
            type_bien = "appartement"
        elif any(k in txt for k in ["villa", "duplex", "triplex"]):
            type_bien = "villa"
        elif any(k in txt for k in ["maison", "dar"]):
            type_bien = "maison"
        elif "terrain" in txt:
            type_bien = "terrain"

        surface_min = None
        m3 = re.search(r"(\d+)\s*m[²2]", txt)
        if m3:
            surface_min = float(m3.group(1))

        rooms_min = None
        m4 = re.search(r"(\d+)\s*(?:chambre|pièce|piece)", txt)
        if m4:
            rooms_min = int(m4.group(1))

        return {
            "ville": None, "budget_max": budget_max, "budget_min": None,
            "type_bien": type_bien, "surface_min": surface_min, "rooms_min": rooms_min,
        }

    # ════════════════════════════════════════════════════════════════════════════
    # BRANCHE DEVIS
    # ════════════════════════════════════════════════════════════════════════════

    def _handle_devis(self, message: str) -> dict:
        projet = self._extract_project(message)

        if not projet.get("infos_suffisantes") or not projet.get("terrain_m2"):
            reponse = self._ask_clarification(message, projet)
            self.history.append({"role": "assistant", "content": reponse})
            return {"texte": reponse, "devis": None, "properties": None}

        try:
            devis = self._compute_devis(projet)
        except Exception as e:
            reponse = (
                f"❌ Une erreur est survenue lors du calcul du devis : {e}\n\n"
                "Veuillez vérifier les informations fournies et réessayer."
            )
            self.history.append({"role": "assistant", "content": reponse})
            return {"texte": reponse, "devis": None, "properties": None}

        texte = self._format_devis_text(devis, projet)
        self.history.append({"role": "assistant", "content": texte})
        return {"texte": texte, "devis": devis, "properties": None}

    # ── Extraction projet ─────────────────────────────────────────────────────

    def _extract_project(self, message: str) -> dict:
        prompt = EXTRACT_PROMPT.format(message=message)
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1, "num_predict": 500},
            )
            raw = response["message"]["content"].strip()
            raw = re.sub(r"```(?:json)?", "", raw).strip("` \n")
            projet = json.loads(raw)
            pieces = projet.get("pieces", {})
            if pieces.get("chambres", 0) > 0 and not pieces.get("dressing"):
                pieces["dressing"] = True
            projet["pieces"] = pieces
            projet = self._validate_and_fix(message, projet)
            return projet
        except Exception:
            return self._extract_regex(message)



    def _normalize_nlp_text(self, message: str) -> str:
        txt = message.lower()
        replacements = {
            "rez-de-chaussée": "rdc",
            "rez de chaussée": "rdc",
            "rez de chaussee": "rdc",
            "1er étage": "niveau 1",
            "1ère étage": "niveau 1",
            "1ere étage": "niveau 1",
            "2ème étage": "niveau 2",
            "2eme étage": "niveau 2",
            "2e étage": "niveau 2",
            "3ème étage": "niveau 3",
            "3eme étage": "niveau 3",
            "3e étage": "niveau 3",
            "4ème étage": "niveau 4",
            "4eme étage": "niveau 4",
            "4e étage": "niveau 4",
            "5ème étage": "niveau 5",
            "5eme étage": "niveau 5",
            "5e étage": "niveau 5",
            "6ème étage": "niveau 6",
            "6eme étage": "niveau 6",
            "6e étage": "niveau 6",
            "7ème étage": "niveau 7",
            "7eme étage": "niveau 7",
            "7e étage": "niveau 7",
            "1er": "1",
            "1ère": "1",
            "1ere": "1",
            "sdb": "salle de bain",
            "appart.": "appartement",
            "apt.": "appartement",
            "apartement": "appartement",
            "apartement": "appartement",
            "apparetement": "appartement",
            "salles de bais": "salles de bain",
            "salle de bai": "salle de bain",
        }
        for a, b in replacements.items():
            txt = txt.replace(a, b)

        num_words = {
            "un": "1", "une": "1",
            "deux": "2", "trois": "3", "quatre": "4", "cinq": "5",
            "six": "6", "sept": "7", "huit": "8", "neuf": "9", "dix": "10"
        }
        for word, digit in num_words.items():
            txt = re.sub(rf"\b{word}\b", digit, txt)
        txt = re.sub(r"\s+", " ", txt).strip()
        return txt

    def _sum_pattern(self, txt: str, pattern: str) -> int:
        matches = re.findall(pattern, txt, flags=re.IGNORECASE)
        total = 0
        for m in matches:
            if isinstance(m, tuple):
                m = next((x for x in m if x), None)
            if m is None:
                continue
            try:
                total += int(m)
            except (TypeError, ValueError):
                pass
        return total

    def _extract_piece_count_in_segment(self, segment: str) -> dict:
        seg = self._normalize_nlp_text(segment)

        counts = {
            "chambres": self._sum_pattern(seg, r"(\d+)\s*chambres?\b"),
            "salons": self._sum_pattern(seg, r"(\d+)\s*salons?\b"),
            "cuisines": self._sum_pattern(seg, r"(\d+)\s*cuisines?\b"),
            "salles_de_bain": self._sum_pattern(seg, r"(\d+)\s*salles?\s+de\s+bains?\b"),
            "wc": self._sum_pattern(seg, r"(\d+)\s*(?:wc|toilettes?)\b"),
        }

        singular_patterns = {
            "salons": r"\bsalon\b",
            "cuisines": r"\bcuisine\b",
            "salles_de_bain": r"\bsalle de bain\b",
            "wc": r"\b(?:wc|toilette)\b",
        }
        for key, pattern in singular_patterns.items():
            if counts[key] == 0 and re.search(pattern, seg):
                counts[key] = 1

        return counts

    def _extract_apartment_contexts(self, message: str) -> list[dict]:
        """
        Extrait les segments pertinents pour les logements.

        Règles anti-double-comptage :
        - Si le message contient des marqueurs de niveaux (RDC, niveau 1, niveau 2, ...)
          on utilise UNIQUEMENT ces segments.
        - Sinon, on retombe sur des segments de type "appartement avec ...".
        """
        txt = self._normalize_nlp_text(message)
        marker_pattern = r"\b(?:rdc|niveau\s*\d+|\d+\s*etage)\b"
        markers = list(re.finditer(marker_pattern, txt))
        contexts = []

        if markers:
            for i, m in enumerate(markers):
                start = m.start()
                end = markers[i + 1].start() if i + 1 < len(markers) else len(txt)
                label = m.group(0)
                segment = txt[start:end].strip(" ,;:-")
                counts = self._extract_piece_count_in_segment(segment)
                is_cafe = any(k in segment for k in ["café", "cafe", "bar", "restaurant", "commerce"])
                is_apartment = ("appartement" in segment or "logement" in segment or "salon" in segment
                                or "cuisine" in segment or "chambre" in segment or "salle de bain" in segment)
                contexts.append({
                    "label": label,
                    "segment": segment,
                    "is_cafe": is_cafe,
                    "is_apartment": is_apartment and not is_cafe,
                    **counts,
                })
            return contexts

        app_segments = re.findall(r"(?:appartement\s+avec[^;\n\.]+)", txt)
        for seg in app_segments:
            counts = self._extract_piece_count_in_segment(seg)
            contexts.append({
                "label": "appartement",
                "segment": seg,
                "is_cafe": False,
                "is_apartment": True,
                **counts,
            })

        dedup, seen = [], set()
        for c in contexts:
            key = c["segment"]
            if key not in seen:
                seen.add(key)
                dedup.append(c)
        return dedup


    def _extract_piece_totals_from_text(self, message: str) -> dict:
        txt = self._normalize_nlp_text(message)

        chambres = self._sum_pattern(txt, r"(\d+)\s*chambres?\b")
        salons   = self._sum_pattern(txt, r"(\d+)\s*salons?\b")
        cuisines = self._sum_pattern(txt, r"(\d+)\s*cuisines?\b")
        sdb      = self._sum_pattern(txt, r"(\d+)\s*salles?\s+de\s+bains?\b")
        wc       = self._sum_pattern(txt, r"(\d+)\s*(?:wc|toilettes?)\b")

        if salons == 0:
            salons = len(re.findall(r"(?<!\d\s)\bsalon\b", txt))
        if cuisines == 0:
            cuisines = len(re.findall(r"(?<!\d\s)\bcuisine\b", txt))
        if sdb == 0:
            sdb = len(re.findall(r"(?<!\d\s)\bsalles? de bains?\b", txt))
        if wc == 0:
            wc = len(re.findall(r"(?<!\d\s)\b(?:wc|toilette)\b", txt))

        return {
            "chambres": chambres,
            "salons": salons,
            "cuisines": cuisines,
            "salles_de_bain": sdb,
            "wc": wc,
        }

    def _extract_structured_counts_from_text(self, message: str) -> dict:
        txt = self._normalize_nlp_text(message)
        contexts = self._extract_apartment_contexts(message)

        explicit_nb_app = None
        m = re.search(r"(\d+)\s*appartements?\b", txt)
        if m:
            explicit_nb_app = int(m.group(1))

        apartment_contexts = [c for c in contexts if c.get("is_apartment")]

        # Cas "5 appartements, chaque appartement contient ..."
        per_apartment_template = bool(
            explicit_nb_app and re.search(r"(?:chaque|chacun des)\s+appartements?.*?(?:contient|avec)", txt)
        )

        if explicit_nb_app is not None:
            nb_app = explicit_nb_app
        elif apartment_contexts:
            level_contexts = [
                c for c in apartment_contexts
                if str(c.get("label", "")).startswith("niveau") or "etage" in str(c.get("label", ""))
            ]
            nb_app = len(level_contexts) if level_contexts else len(apartment_contexts)
        else:
            nb_app = 0

        global_totals = self._extract_piece_totals_from_text(message)

        if per_apartment_template and explicit_nb_app:
            totals = {
                "chambres": int(global_totals.get("chambres", 0)) * explicit_nb_app,
                "salons": int(global_totals.get("salons", 0)) * explicit_nb_app,
                "cuisines": int(global_totals.get("cuisines", 0)) * explicit_nb_app,
                "salles_de_bain": int(global_totals.get("salles_de_bain", 0)) * explicit_nb_app,
                "wc": int(global_totals.get("wc", 0)) * explicit_nb_app,
            }
        elif apartment_contexts:
            totals = {"chambres": 0, "salons": 0, "cuisines": 0, "salles_de_bain": 0, "wc": 0}
            for c in apartment_contexts:
                for k in totals:
                    totals[k] += int(c.get(k, 0) or 0)
        else:
            totals = global_totals

        if any(x in txt for x in ["au total", "en total", "total", "totale"]):
            for k, v in global_totals.items():
                if v > 0:
                    totals[k] = v

        # Cas hôtel / foyer : "dans chaque étage 5 chambres et 5 salles de bain"
        each_floor = re.search(
            r"(?:chaque\s+etage|dans\s+chaque\s+etage|par\s+etage).*?(\d+)\s*chambres?.*?(\d+)\s*salles?\s+de\s+bains?",
            txt
        )
        if each_floor:
            per_floor_ch = int(each_floor.group(1))
            per_floor_sdb = int(each_floor.group(2))
            m_floors = re.search(r"(\d+)\s*[eè]tages?", message.lower())
            guest_floors = int(m_floors.group(1)) if m_floors else max(1, len([c for c in contexts if c.get("is_apartment")]))
            totals["chambres"] = per_floor_ch * guest_floors
            totals["salles_de_bain"] = per_floor_sdb * guest_floors

        has_cafe = any(w in txt for w in ["café", "cafe", "bar", "restaurant", "commerce"])
        return {
            "nb_appartements": nb_app,
            "pieces": totals,
            "has_cafe": has_cafe,
            "contexts": contexts,
        }
    def _has_explicit_multi_level(self, message: str) -> bool:
        txt = message.lower()
        patterns = [
            r"\brdc\b",
            r"rez[- ]de[- ]chauss[ée]e",
            r"\b\d+\s*niveaux?\b",
            r"\b\d+\s*[eè]tages?\b",
            r"\b(?:1er|1ere|1ère|2eme|2ème|3eme|3ème|premier|deuxième|deuxieme|troisième|troisieme)\s+[eé]tage\b",
            r"duplex",
            r"triplex",
            r"en haut",
            r"au-dessus",
        ]
        return any(re.search(p, txt) for p in patterns)

    def _validate_and_fix(self, message: str, projet: dict) -> dict:
        """
        Corrige les erreurs de calcul du LLM :
        1. nombre_etages : "2 étages" = 3 niveaux, "2 niveaux" = 2 niveaux
        2. type_projet : mixte_maison_appart vs mixte_cafe_appart
        3. nb_appartements : compte depuis le message (plus fiable)
        4. Forcer nombre_etages=1 si aucun mot multi-niveaux
        """
        txt = message.lower()
        type_p = projet.get("type_projet", "construction")

        # ── 1. Correction nombre_etages ───────────────────────────────────────
        #   "X étages" (sans "niveaux") → RDC + X = X+1 niveaux
        #   "X niveaux" → X niveaux
        #   "le 1er et le 2ème étage" (2 appartements distincts) → 2 niveaux
        #   NB : le LLM confond souvent les deux → on re-calcule depuis le texte
        m_niveaux = re.search(r"(\d+)\s*niveaux?", txt)
        m_etages  = re.search(r"(\d+)\s*[eè]tages?", txt)

        nb_appart_in_msg = len(re.findall(
            r'\b(?:un appartement|une appartement|le \d+[eè]me? [eé]tage un|le \d+[eè]re? [eé]tage un)',
            txt
        ))
        m_ap_explicit = re.search(r'(\d+)\s*appartements?', txt)
        if m_ap_explicit:
            nb_appart_in_msg = int(m_ap_explicit.group(1))

        if m_niveaux:
            # "2 niveaux" → 2 niveaux
            projet["nombre_etages"] = int(m_niveaux.group(1))
        elif m_etages:
            # En Tunisie, "2 étages" signifie généralement 2 niveaux TOTAL
            # (RDC = rez-de-chaussée = "étage 1", 1er étage = "étage 2")
            # SAUF si l'utilisateur dit explicitement "RDC + X étages" ou mentionne le RDC séparément
            nb_et_txt = int(m_etages.group(1))
            has_explicit_rdc = any(w in txt for w in [
                "rdc", "rez-de-chaussée", "rez de chaussée",
                "en bas", "au rez", "plain-pied"
            ])
            if has_explicit_rdc:
                # Contexte clair : RDC + étages → nb_et_txt + 1 niveaux
                projet["nombre_etages"] = nb_et_txt + 1
            else:
                # Usage courant tunisien : "2 étages" = 2 niveaux total
                projet["nombre_etages"] = nb_et_txt
        elif nb_appart_in_msg > 0:
            # "appartement au 1er étage + appartement au 2ème étage" → déduit
            # On assume RDC (maison ou cave) + nb_appart niveaux
            has_rdc_explicit = any(w in txt for w in ["rdc", "rez-de-chaussée", "rez de chaussée"])
            if has_rdc_explicit:
                projet["nombre_etages"] = 1 + nb_appart_in_msg
            else:
                # Pas de RDC séparé → nb_appart niveaux occupés
                projet["nombre_etages"] = max(2, nb_appart_in_msg)

        # Forcer nombre_etages=1 si aucun mot multi-niveaux
        MULTI_LEVEL_WORDS = [
            "étage", "etage", "niveaux", "niveau", "en haut", "au-dessus",
            "2ème", "2eme", "3ème", "3eme", "4ème", "4eme",
            "premier étage", "deuxième", "troisième", "duplex", "triplex",
            "appartement", "appart",
        ]
        MULTI_TYPES = {"mixte_cafe_appart", "mixte_maison_appart", "hotel",
                       "foyer", "bureau", "clinique", "salle_fetes"}
        if (not any(w in txt for w in MULTI_LEVEL_WORDS)
                and projet.get("type_projet") not in MULTI_TYPES):
            projet["nombre_etages"] = 1

        # ── 2. Correction nb_appartements ─────────────────────────────────────
        nb_appart_llm = int(projet.get("nb_appartements") or 0)
        nombre_etages = int(projet.get("nombre_etages") or 1)

        if nb_appart_in_msg > 0:
            # Le regex a trouvé un nombre explicite → priorité absolue
            nb_appartements_final = nb_appart_in_msg
        elif nb_appart_llm > 0:
            # Le LLM a extrait un nombre → on lui fait confiance
            nb_appartements_final = nb_appart_llm
        elif nombre_etages > 1:
            # Fallback : autant d'appartements que de niveaux (pas niveaux-1)
            # car chaque niveau est un logement indépendant dans le contexte tunisien
            nb_appartements_final = nombre_etages
        else:
            nb_appartements_final = 0

        projet["nb_appartements"] = nb_appartements_final

        # ── 3. Correction type_projet ─────────────────────────────────────────
        CAFE_WORDS = ["café", "cafe", "bar", "restaurant", "commerce", "boutique",
                      "local commercial", "magasin", "pizzeria", "brasserie"]
        has_cafe = any(w in txt for w in CAFE_WORDS)
        APPART_WORDS = ["appartement", "appart", "studio", "logement", "résidence"]
        has_appart = any(w in txt for w in APPART_WORDS)
        has_multi_logement = any(w in txt for w in [
            "maison", "villa", "habitation", "logement", "étage", "etage",
            "niveaux", "niveau", "en haut", "au-dessus"
        ])

        # mixte_cafe_appart exige un mot café EXPLICITE
        if type_p == "mixte_cafe_appart" and not has_cafe:
            if has_appart and has_multi_logement:
                projet["type_projet"] = "mixte_maison_appart"
            else:
                projet["type_projet"] = "construction"

        # Détecter mixte_maison_appart non capturé par LLM
        if type_p in ("construction", "appartement") and nb_appartements_final >= 1:
            has_multi_kw = any(w in txt for w in ["étage", "etage", "niveau", "niveaux", "en haut"])
            has_logement_kw = any(w in txt for w in ["appartement", "appart", "maison", "logement", "habitation"])
            if has_multi_kw and has_logement_kw and not has_cafe:
                projet["type_projet"] = "mixte_maison_appart"
        
        # Forcer mixte_maison_appart si plusieurs niveaux décrits avec pièces distinctes par niveau
        if type_p == "construction" and nombre_etages >= 2 and not has_cafe:
            # Si l'utilisateur décrit des pièces par niveau → multi-logements
            per_level_pattern = re.search(
                r'(?:1er|2[eè]me?|premier|deuxi[eè]me?|troisi[eè]me?)\s+[eé]tage',
                txt
            )
            if per_level_pattern:
                projet["type_projet"] = "mixte_maison_appart"
                if nb_appartements_final == 0:
                    nb_appartements_final = nombre_etages
                    projet["nb_appartements"] = nb_appartements_final

        # appartement sans mot "appartement" → corriger
        if projet.get("type_projet") == "appartement" and not has_appart:
            if any(w in txt for w in ["villa", "duplex", "triplex"]):
                projet["type_projet"] = "villa"
            else:
                projet["type_projet"] = "construction"

        # cafe_commerce + appartements → mixte_cafe_appart
        if type_p == "cafe_commerce":
            nb_ch = (projet.get("pieces") or {}).get("chambres", 0) or 0
            if nb_ch > 0 and has_appart and has_cafe:
                projet["type_projet"] = "mixte_cafe_appart"

        # ── 4. Correction NLP structurée : appartements + pièces totalisées ──
        structured = self._extract_structured_counts_from_text(message)
        pieces = projet.get("pieces", {}) or {}
        forced_pieces = structured.get("pieces", {}) or self._extract_piece_totals_from_text(message)
        for key in ["chambres", "salons", "cuisines", "salles_de_bain", "wc"]:
            if forced_pieces.get(key, 0) > 0:
                pieces[key] = forced_pieces[key]

        if structured.get("nb_appartements", 0) > 0:
            projet["nb_appartements"] = structured["nb_appartements"]

        if structured.get("has_cafe") and projet.get("nb_appartements", 0) > 0:
            projet["type_projet"] = "mixte_cafe_appart"

        if "appartement" in txt and projet.get("nb_appartements", 0) <= 1 and not structured.get("has_cafe"):
            if not self._has_explicit_multi_level(message):
                projet["type_projet"] = "appartement"
                projet["nombre_etages"] = 1
                projet["nb_appartements"] = 1

        if projet.get("nb_appartements", 0) > 1 and not structured.get("has_cafe"):
            projet["type_projet"] = "mixte_maison_appart"
            if not self._has_explicit_multi_level(message):
                projet["nombre_etages"] = max(1, projet["nb_appartements"])

        # Cas hôtel / foyer : si l'utilisateur donne des quantités par étage, on multiplie
        each_floor = re.search(
            r"(?:chaque\s+[eé]tage|dans\s+chaque\s+[eé]tage|par\s+[eé]tage).*?(\d+)\s*chambres?.*?(\d+)\s*salles?\s+de\s+bain",
            txt
        )
        if each_floor and projet.get("type_projet") in ("hotel", "foyer"):
            guest_floors = max(1, int(projet.get("nombre_etages") or 1) - 1)
            pieces["chambres"] = int(each_floor.group(1)) * guest_floors
            pieces["salles_de_bain"] = int(each_floor.group(2)) * guest_floors
            pieces["cuisines"] = max(int(pieces.get("cuisines", 0) or 0), 1)

        pieces["dressing"] = bool(pieces.get("dressing") or pieces.get("chambres", 0) > 0)
        projet["pieces"] = pieces

        # Si aucun mot-clé multi-niveaux n'est explicitement présent,
        # on force une maison/appartement simple à 1 niveau.
        if not self._has_explicit_multi_level(message):
            if projet.get("type_projet") not in {"hotel", "foyer", "bureau", "clinique", "salle_fetes", "mixte_cafe_appart", "mixte_maison_appart"}:
                projet["nombre_etages"] = 1
                if projet.get("type_projet") in {"construction", "villa", "appartement"}:
                    projet["nb_appartements"] = 0

        return projet

    def _extract_regex(self, message: str) -> dict:
        """Fallback regex si le LLM échoue."""
        txt = message.lower()

        # Surface terrain
        terrain = None
        m = re.search(r"(\d[\d\s]*)[\s]*m[²2]", txt)
        if m:
            terrain = float(re.sub(r"\s", "", m.group(1)))

        # Détection café + appartements
        has_cafe = any(k in txt for k in ["café", "cafe", "bar", "restaurant",
                                           "commerce", "local commercial", "boutique"])
        has_appart_kw = any(k in txt for k in ["appartement", "appart", "logement"])
        is_mixte = has_cafe and has_appart_kw and any(k in txt for k in [
            "rdc", "rez de chaussée", "rez-de-chaussée", "en bas", "en haut",
            "étage", "etage", "dessus", "au-dessus", "premier", "deuxième", "niveau"
        ])

        structured = self._extract_structured_counts_from_text(message)

        # Nombre d'appartements (NLP > regex simple)
        nb_appart = int(structured.get("nb_appartements") or 0)
        if nb_appart == 0:
            m_ap = re.search(r"(\d+)\s*appartement", txt)
            if m_ap:
                nb_appart = int(m_ap.group(1))
            elif is_mixte and has_appart_kw:
                nb_appart = 1
            elif has_appart_kw:
                nb_appart = len(re.findall(r'\d+[eè][rm]?e?\s*[eé]tage', txt))
                if nb_appart == 0:
                    nb_appart = 1

        # ── Nombre de niveaux — CORRECTION BUG PRINCIPAL ──────────────────────
        nombre_etages = 1
        m_niv = re.search(r"(\d+)\s*niveaux?", txt)
        m_et  = re.search(r"(\d+)\s*[eè]tages?", txt)
        if m_niv:
            nombre_etages = int(m_niv.group(1))
        elif m_et:
            nb_et_txt = int(m_et.group(1))
            # Usage tunisien : "2 étages" = 2 niveaux total (pas RDC+2)
            has_explicit_rdc = any(w in txt for w in [
                "rdc", "rez-de-chaussée", "rez de chaussée", "en bas", "plain-pied"
            ])
            nombre_etages = nb_et_txt + 1 if has_explicit_rdc else nb_et_txt
        elif is_mixte and nb_appart > 0:
            nombre_etages = 1 + nb_appart
        elif has_appart_kw and nb_appart > 0:
            # Maison/cage + appartements aux étages
            has_rdc = any(w in txt for w in ["rdc", "rez de chaussée", "maison", "villa"])
            nombre_etages = (1 + nb_appart) if has_rdc else nb_appart
        elif re.search(r"(rdc|rez.de.chauss)", txt) and re.search(r"\+\s*(\d+)", txt):
            m_rdc = re.search(r"\+\s*(\d+)", txt)
            if m_rdc:
                nombre_etages = 1 + int(m_rdc.group(1))
        elif "duplex" in txt:
            nombre_etages = 2
        elif "triplex" in txt:
            nombre_etages = 3

        MULTI_WORDS_R = ["en haut", "étage", "etage", "2ème", "2eme", "niveaux", "niveau",
                         "deuxième", "troisième", "au-dessus", "duplex", "triplex"]
        if not any(w in txt for w in MULTI_WORDS_R) and not (is_mixte or nb_appart > 0):
            nombre_etages = 1

        explicit_totals = structured.get("pieces") or self._extract_piece_totals_from_text(message)
        chambres_raw = explicit_totals.get("chambres", 0)
        salons_raw   = explicit_totals.get("salons", 0) or (1 if "salon" in txt else 0)
        cuisines_raw = explicit_totals.get("cuisines", 0) or (1 if "cuisine" in txt else 0)
        sdb_raw      = explicit_totals.get("salles_de_bain", 0) or (1 if "salle" in txt and "bain" in txt else 0)
        wc_raw       = explicit_totals.get("wc", 0) or (1 if "wc" in txt or "toilette" in txt else 0)

        # NE PAS multiplier les pièces — l'utilisateur donne déjà le total par niveau décrit
        chambres, salons, cuisines, sdb, wc = chambres_raw, salons_raw, cuisines_raw, sdb_raw, wc_raw

        jardin   = "jardin" in txt
        piscine  = "piscine" in txt
        dressing = "dressing" in txt or "placard" in txt or chambres > 0

        # Type de projet
        if is_mixte:
            type_projet = "mixte_cafe_appart"
        elif any(k in txt for k in ["rénov", "renov", "refaire"]):
            type_projet = "renovation"
        elif any(k in txt for k in ["hôtel", "hotel"]):
            type_projet = "hotel"
        elif any(k in txt for k in ["foyer", "résidence étudiante"]):
            type_projet = "foyer"
        elif any(k in txt for k in ["esthétique", "esthetique", "spa", "hammam"]):
            type_projet = "centre_esthetique"
        elif any(k in txt for k in ["salle de sport", "gym", "fitness"]):
            type_projet = "salle_sport"
        elif any(k in txt for k in ["clinique", "cabinet médical", "dentiste"]):
            type_projet = "clinique"
        elif any(k in txt for k in ["bureau", "bureaux", "coworking"]):
            type_projet = "bureau"
        elif any(k in txt for k in ["salle des fêtes", "salle de mariage"]):
            type_projet = "salle_fetes"
        elif any(k in txt for k in ["entrepôt", "entrepot", "hangar"]):
            type_projet = "entrepot"
        elif has_cafe:
            type_projet = "cafe_commerce"
        elif "villa" in txt:
            type_projet = "villa"
        elif has_appart_kw and nb_appart > 0:
            has_maison_rdc = any(w in txt for w in ["maison", "villa", "habitation"])
            has_etage_loc  = any(w in txt for w in ["en haut", "étage", "etage", "au-dessus"])
            if has_maison_rdc and has_etage_loc:
                type_projet = "mixte_maison_appart"
            else:
                # Plusieurs appartements empilés sans maison RDC = mixte aussi
                type_projet = "mixte_maison_appart" if nb_appart > 1 else "appartement"
        elif nombre_etages >= 2 and not has_cafe:
            # Multi-niveaux avec pièces décrites par niveau → multi-logements
            per_level = re.search(
                r'(?:1er|2[eè]me?|premier|deuxi[eè]me?|troisi[eè]me?)\s+[eé]tage',
                txt
            )
            if per_level:
                type_projet = "mixte_maison_appart"
                if nb_appart == 0:
                    nb_appart = nombre_etages
            else:
                type_projet = "construction"
        else:
            type_projet = "construction"

        infos_ok = terrain is not None and (
            (chambres + salons + cuisines + sdb) > 0
            or type_projet in ("hotel", "foyer", "centre_esthetique", "salle_sport",
                               "clinique", "bureau", "salle_fetes", "entrepot",
                               "cafe_commerce", "mixte_cafe_appart", "mixte_maison_appart")
        )

        projet_raw = {
            "terrain_m2":      terrain,
            "nombre_etages":   nombre_etages,
            "type_projet":     type_projet,
            "nb_appartements": nb_appart if nb_appart > 0 else nombre_etages if nombre_etages > 1 else None,
            "pieces": {
                "chambres": chambres, "salons": salons, "cuisines": cuisines,
                "salles_de_bain": sdb, "wc": wc, "jardin": jardin,
                "piscine": piscine, "dressing": dressing,
            },
            "qualite": "standard",
            "infos_suffisantes": infos_ok,
        }
        return self._validate_and_fix(message, projet_raw)

    def _ask_clarification(self, message: str, projet: dict) -> str:
        manquants = []
        if not projet.get("terrain_m2"):
            manquants.append("la surface du terrain ou du local (en m²)")
        pieces = projet.get("pieces", {})
        type_p = projet.get("type_projet", "construction")
        is_commercial = type_p in ("hotel", "foyer", "centre_esthetique", "salle_sport",
                                   "clinique", "bureau", "salle_fetes", "entrepot",
                                   "cafe_commerce")
        if not is_commercial and (
            not pieces
            or (pieces.get("chambres", 0) == 0
                and pieces.get("salons", 0) == 0
                and pieces.get("cuisines", 0) == 0)
        ):
            manquants.append("les pièces souhaitées (chambres, salon, cuisine…)")

        if manquants:
            return (
                "Pour préparer votre devis, j'ai besoin de :\n"
                + "\n".join(f"- {m}" for m in manquants)
                + "\n\nPouvez-vous préciser ?"
            )
        return "Pourriez-vous préciser votre projet ?"

    def _compute_devis(self, projet: dict) -> dict:
        terrain_m2    = float(projet.get("terrain_m2") or 0)
        pieces_raw    = projet.get("pieces", {})
        nombre_etages = int(projet.get("nombre_etages") or 1)

        _raw_type   = str(projet.get("type_projet", "construction")).lower().strip()
        type_projet = _TYPE_NORM.get(_raw_type, "construction")
        nb_appartements = int(projet.get("nb_appartements") or 0)

        def _int(val, default=0):
            try:
                return int(val) if val is not None else default
            except (TypeError, ValueError):
                return default

        _msg     = self.history[-1]["content"].lower() if self.history else ""
        _jardin  = bool(pieces_raw.get("jardin") or False) or "jardin" in _msg
        _piscine = bool(pieces_raw.get("piscine") or False) or "piscine" in _msg

        pieces = {
            "chambres":      _int(pieces_raw.get("chambres"), 0),
            "salons":        _int(pieces_raw.get("salons"), 0),
            "cuisines":      _int(pieces_raw.get("cuisines"), 0),
            "salle_de_bain": _int(pieces_raw.get("salles_de_bain"), 0),
            "wc":            _int(pieces_raw.get("wc"), 0),
            "jardin":        _jardin,
            "piscine":       _piscine,
            "dressing":      bool(pieces_raw.get("dressing") or pieces_raw.get("chambres", 0) > 0),
            "nombre_etages": nombre_etages,
            "_type_projet":  type_projet,
            "_nb_appartements": nb_appartements,
        }

        description  = self._build_description(type_projet, pieces, nombre_etages)
        rag_prices   = self.retriever.get_prices_for_project(description)
        if "_meta" not in rag_prices:
            rag_prices["_meta"] = {}
        rag_prices["_meta"]["mode"] = type_projet

        surfaces = self.calculator.estimate_surfaces(terrain_m2, pieces, nombre_etages)
        devis    = self.calculator.build_devis(surfaces, rag_prices, pieces)
        devis["_meta"]          = rag_prices.get("_meta", {})
        devis["_nombre_etages"] = nombre_etages
        return devis

    def _build_description(self, type_projet: str, pieces: dict, nombre_etages: int = 1) -> str:
        type_map = {
            "renovation":           "rénovation maison",
            "mixte_cafe_appart":    "café commerce local commercial appartement construction",
            "mixte_maison_appart":  "construction maison appartement résidentiel",
            "cafe_commerce":        "café commerce local commercial",
            "villa":                "villa construction",
            "appartement":          "appartement construction",
            "construction":         "construction maison",
            "hotel":                "hôtel résidence hôtelière construction",
            "foyer":                "foyer résidence étudiante construction",
            "centre_esthetique":    "centre esthétique spa salon de beauté construction",
            "salle_sport":          "salle de sport gym fitness construction",
            "clinique":             "clinique cabinet médical construction",
            "bureau":               "bureaux open space coworking construction",
            "salle_fetes":          "salle des fêtes réception mariage construction",
            "entrepot":             "entrepôt hangar construction",
        }
        base  = type_map.get(type_projet, "construction")
        parts = [base]
        if nombre_etages > 1:
            parts.append(f"{nombre_etages} étages escalier")
        if pieces.get("chambres"):     parts.append(f"{pieces['chambres']} chambres")
        if pieces.get("salons"):       parts.append("salon")
        if pieces.get("cuisines"):     parts.append("cuisine")
        if pieces.get("salle_de_bain"): parts.append("salle de bain")
        if pieces.get("jardin"):       parts.append("jardin")
        if pieces.get("piscine"):      parts.append("piscine")
        if pieces.get("dressing"):     parts.append("dressing placard")
        return " ".join(parts)

    # ── Formatage devis ────────────────────────────────────────────────────────

    def _format_devis_text(self, devis: dict, projet: dict) -> str:
        resume   = devis.get("resume", {})
        postes   = devis.get("postes", {})
        total    = devis.get("total", {})
        acc      = devis.get("accuracy", {})

        terrain       = resume.get("terrain", "?")
        surf_plancher = resume.get("surface_plancher", resume.get("surface_habitable", "?"))
        surf_hab      = resume.get("surface_habitable", "?")
        surf_emprise  = resume.get("emprise_sol", "")
        surf_jrd      = resume.get("surface_jardin", "0 m²")
        surf_all      = resume.get("surface_allee", "0 m²")
        surf_pis      = resume.get("surface_piscine", "")
        nb_et         = devis.get("_nombre_etages", 1)

        t_min = total.get("total_min_str", "—")
        t_mid = total.get("total_mid_str", "—")
        t_max = total.get("total_max_str", "—")
        acc_score   = acc.get("score", 0)
        acc_qualite = acc.get("qualite", "")
        acc_detail  = acc.get("detail", "")
        nb_ds  = acc.get("postes_dataset", 0)
        nb_tot = acc.get("postes_total", 0)

        type_labels = {
            "construction":       "🏗️ Construction Maison",
            "villa":              "🏡 Villa",
            "appartement":        "🏢 Appartement",
            "renovation":         "🔨 Rénovation",
            "cafe_commerce":      "☕ Café / Commerce",
            "mixte_cafe_appart":  "🏗️ Café + Appartements",
            "mixte_maison_appart":"🏠 Maison + Appartements",
            "hotel":              "🏨 Hôtel / Résidence",
            "foyer":              "🏠 Foyer / Résidence",
            "centre_esthetique":  "💆 Centre Esthétique / Spa",
            "salle_sport":        "🏋️ Salle de Sport / Gym",
            "clinique":           "🏥 Clinique / Cabinet Médical",
            "bureau":             "🏢 Bureaux / Open Space",
            "salle_fetes":        "🎉 Salle des Fêtes / Réception",
            "entrepot":           "🏭 Entrepôt / Hangar",
        }
        type_projet = devis.get("_meta", {}).get("mode", "construction")
        titre_type  = type_labels.get(type_projet, "🏗️ Construction")

        header_parts = [f"**Terrain :** {terrain}"]
        if nb_et > 1:
            header_parts.append(f"**Emprise au sol :** {surf_emprise}")
            header_parts.append(f"**Nombre de niveaux :** {nb_et}")
            header_parts.append(f"**Surface plancher totale :** {surf_plancher} *(tous niveaux)*")
            header_parts.append(f"**Surface utile :** {surf_hab}")
        else:
            header_parts.append(f"**Surface habitable :** {surf_hab}")
        if surf_all and surf_all != "0 m²":
            header_parts.append(f"**Parking/accès :** {surf_all}")
        if surf_jrd and surf_jrd != "0 m²":
            header_parts.append(f"**Jardin :** {surf_jrd}")
        if surf_pis:
            header_parts.append(f"**Piscine :** {surf_pis}")

        lines = [
            f"## {titre_type} — Tunisie 2025", "",
            "  &nbsp;|&nbsp;  ".join(header_parts), "",
            "| # | Poste de travaux | Qté | MIN (DT) | MOY (DT) | MAX (DT) |",
            "|:-:|:----------------|:---:|--------:|--------:|--------:|",
        ]

        ICONS = {
            "gros_oeuvre": "🏛️", "carrelage_sol": "🪨", "faience": "🔷",
            "isolation": "🧱", "peinture": "🖌️", "electricite": "⚡",
            "plomberie": "🚰", "fenetre": "🪟", "porte_fenetre": "🚪",
            "porte_blindee": "🔒", "porte_interieure": "🚪",
            "portes_interieures": "🚪", "cuisine_equipee": "🍳",
            "cuisine_appart": "🍳", "cuisine_cafe": "🍳",
            "salle_de_bain": "🚿", "chauffe_eau": "🌡️", "climatisation": "❄️",
            "dressing": "👔", "raccord_eau": "💧", "raccord_gaz": "🔥",
            "raccord_elec": "🔌", "securite": "🔐", "jardin": "🌿",
            "piscine": "🏊", "faux_plafond": "🏠", "fenetres": "🪟",
            "escalier": "🪜", "ascenseur": "🛗",
        }

        def _fmt(v):
            try:
                return f"{int(round(float(v))):,}".replace(",", "\u202f")
            except Exception:
                return str(v)

        for i, (key, p) in enumerate(postes.items(), 1):
            icon    = ICONS.get(key, "🔧")
            desc    = p.get("description", key)
            qte     = p.get("quantite", 1)
            unite   = p.get("unite", "")
            c_min   = _fmt(p.get("cout_min", 0))
            c_mid   = _fmt(p.get("cout_mid", 0))
            c_max   = _fmt(p.get("cout_max", 0))
            qte_str = f"{qte} {unite}" if unite else str(qte)
            lines.append(f"| {i} | {icon} {desc} | {qte_str} | {c_min} | {c_mid} | {c_max} |")

        lines.append(
            f"| | **💰 TOTAL** *(imprévus 10% inclus)* | | "
            f"**{t_min}** | **{t_mid}** | **{t_max}** |"
        )
        lines += [
            "", "---",
            f"### 💰 Fourchette totale : **{t_min} → {t_max}**",
            f"*(Estimation moyenne recommandée : **{t_mid}**)*", "", "---",
            "**Légende qualité :**", "",
            "| Niveau | Description |", "|:------:|:------------|",
            "| **MIN** | Matériaux économiques, main-d'œuvre standard |",
            "| **MOY** | Qualité intermédiaire — *recommandée* |",
            "| **MAX** | Matériaux premium, finitions haut de gamme |", "", "---",
            f"### 🎯 Précision du devis : {acc_qualite} — **{acc_score}%**",
            f"*{nb_ds} sur {nb_tot} postes calculés directement depuis le dataset de prix tunisien.*",
            f"> {acc_detail}", "",
            "> ⚠️ *Hors honoraires architecte (5–8% du total) et taxes.*",
        ]

        # ── BLOC ML — affiché si le predictor a ajusté le devis ──────────────
        pred = devis.get("prediction")
        if pred:
            conf_icons = {"haute": "🟢", "moyenne": "🟡", "faible": "🔴"}
            icon       = conf_icons.get(pred.get("confidence", "faible"), "⚪")
            r2_val     = pred.get("r2_score")
            r2_str     = f"R²={r2_val:.2f}" if r2_val is not None else "bootstrap"
            alpha      = pred.get("blend_alpha", 0.35)
            n_train    = pred.get("n_train", 0)
            model_name = pred.get("model", "ML")

            rules_min = pred.get("rules_min", 0)
            rules_mid = pred.get("rules_mid", 0)
            rules_max = pred.get("rules_max", 0)
            ml_min    = pred.get("ml_min", 0)
            ml_mid    = pred.get("ml_mid", 0)
            ml_max    = pred.get("ml_max", 0)

            lines += [
                "", "---",
                f"### 🤖 Prédiction ML — Confiance : {icon} {pred.get('confidence', '').capitalize()}",
                "",
                "| | MIN (DT) | MOY (DT) | MAX (DT) |",
                "|:---|:---:|:---:|:---:|",
                f"| 📐 Règles RAG seules | {_fmt(rules_min)} | {_fmt(rules_mid)} | {_fmt(rules_max)} |",
                f"| 🤖 Prédiction ML seule | {_fmt(ml_min)} | {_fmt(ml_mid)} | {_fmt(ml_max)} |",
                f"| **✅ Résultat blendé** | **{t_min}** | **{t_mid}** | **{t_max}** |",
                "",
                f"> *Blend α={alpha} ({int((1-alpha)*100)}% règles + {int(alpha*100)}% ML) "
                f"• {model_name} • {r2_str} • {n_train} devis d'entraînement*",
            ]
        # ─────────────────────────────────────────────────────────────────────

        return "\n".join(lines)

    # ── Réinitialisation ──────────────────────────────────────────────────────

    def reset(self):
        self.history = []