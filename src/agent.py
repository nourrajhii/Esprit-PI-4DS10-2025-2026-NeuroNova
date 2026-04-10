"""
ConstructionAgent v3.0
─────────────────────────────────────────────────────────────
Nouveautés v3.0 :
  - Extraction JSON enrichie : piscine, dressing, nb_sdb
  - Regex fallback étendu : piscine, dressing, nombre de SDB
  - Description projet enrichie pour le RAGRetriever
─────────────────────────────────────────────────────────────
"""

import re
import json
from typing import Optional

import ollama

from .rag_retriever import RAGRetriever
from .devis_calculator import DevisCalculator


# ── Prompt système ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Tu es un expert en construction et rénovation en Tunisie.
Tu aides les clients à obtenir une estimation du coût de leur projet.

Ton rôle :
1. Extraire les informations clés du message de l'utilisateur :
   - Surface du terrain (m²)
   - Type de projet : construction neuve, rénovation, café/commerce, appartement, villa
   - Pièces souhaitées : chambres, salon, cuisine, salle de bain, WC, jardin, piscine, dressing
   - Préférences qualité : économique, standard, premium

2. Répondre en français, de façon professionnelle et concise.
3. Si des informations manquent pour calculer le devis, poser UNE seule question précise.
4. Quand tu as suffisamment d'informations, indiquer que le devis va être calculé.

Règles importantes :
- Ne jamais inventer de prix
- Les prix viennent exclusivement du dataset de marché tunisien 2025
- Toujours inclure une fourchette MIN / MOY / MAX
- Mentionner que les prix sont hors honoraires architecte (5–8%)
"""

EXTRACT_PROMPT = """À partir du message suivant, extrais les informations du projet de construction.

Message : {message}

Réponds UNIQUEMENT avec un objet JSON valide, sans texte autour, sans balises markdown.
Format exact :
{{
  "terrain_m2": <nombre ou null>,
  "type_projet": "<construction|renovation|cafe_commerce|appartement|villa>",
  "pieces": {{
    "chambres": <nombre>,
    "salons": <nombre>,
    "cuisines": <nombre>,
    "salles_de_bain": <nombre>,
    "wc": <nombre>,
    "jardin": <true|false>,
    "piscine": <true|false>,
    "dressing": <true|false>
  }},
  "qualite": "<economique|standard|premium>",
  "infos_suffisantes": <true|false>
}}

Règles :
- jardin = true si le message mentionne "jardin"
- piscine = true si le message mentionne "piscine"
- dressing = true si le message mentionne "dressing" ou "placard" ou "chambre" (chaque chambre aura son dressing)
- Si une information est absente, mets null ou 0 selon le cas.
- infos_suffisantes = true si on a au minimum terrain_m2 et au moins une pièce.
"""


# ── Classe principale ─────────────────────────────────────────────────────────

class ConstructionAgent:

    def __init__(self,
                 retriever: RAGRetriever,
                 calculator: DevisCalculator,
                 model: str = "llama3.2:1b"):
        self.retriever  = retriever
        self.calculator = calculator
        self.model      = model
        self.history    = []

    # ── Entrée principale ─────────────────────────────────────────────────────

    def chat(self, message: str) -> dict:
        self.history.append({"role": "user", "content": message})

        projet = self._extract_project(message)

        if not projet.get("infos_suffisantes") or not projet.get("terrain_m2"):
            reponse = self._ask_clarification(message, projet)
            self.history.append({"role": "assistant", "content": reponse})
            return {"texte": reponse, "devis": None}

        try:
            devis = self._compute_devis(projet)
        except Exception as e:
            reponse = (
                f"❌ Une erreur est survenue lors du calcul du devis : {e}\n\n"
                "Veuillez vérifier les informations fournies et réessayer."
            )
            self.history.append({"role": "assistant", "content": reponse})
            return {"texte": reponse, "devis": None}

        texte = self._format_devis_text(devis, projet)
        self.history.append({"role": "assistant", "content": texte})

        return {"texte": texte, "devis": devis}

    # ── Extraction des paramètres projet ──────────────────────────────────────

    def _extract_project(self, message: str) -> dict:
        prompt = EXTRACT_PROMPT.format(message=message)

        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1, "num_predict": 400},
            )
            raw = response["message"]["content"].strip()
            raw = re.sub(r"```(?:json)?", "", raw).strip("` \n")
            projet = json.loads(raw)

            # S'assurer que dressing est true si chambres > 0
            pieces = projet.get("pieces", {})
            if pieces.get("chambres", 0) > 0 and not pieces.get("dressing"):
                pieces["dressing"] = True
            projet["pieces"] = pieces

            return projet

        except Exception:
            return self._extract_regex(message)

    def _extract_regex(self, message: str) -> dict:
        """Extraction heuristique par regex si le LLM échoue ou est absent."""
        txt = message.lower()

        # Terrain
        terrain = None
        m = re.search(r"(\d[\d\s]*)[\s]*m[²2]", txt)
        if m:
            terrain = float(re.sub(r"\s", "", m.group(1)))

        def _nb(pattern):
            m2 = re.search(pattern, txt)
            return int(m2.group(1)) if m2 else 0

        chambres   = _nb(r"(\d+)\s*chambre")
        salons     = _nb(r"(\d+)\s*salon") or (1 if "salon" in txt else 0)
        cuisines   = 1 if "cuisine" in txt else 0
        sdb        = _nb(r"(\d+)\s*salle") or (1 if "salle" in txt else 0)
        wc         = _nb(r"(\d+)\s*(?:wc|toilette)") or (1 if "wc" in txt or "toilette" in txt else 0)
        jardin     = "jardin" in txt
        piscine    = "piscine" in txt
        # dressing = explicitement demandé OU chaque chambre en a un
        dressing   = "dressing" in txt or "placard" in txt or chambres > 0

        if any(k in txt for k in ["rénov", "renov", "refaire"]):
            type_projet = "renovation"
        elif any(k in txt for k in ["café", "cafe", "restaurant", "commerce"]):
            type_projet = "cafe_commerce"
        elif "villa" in txt:
            type_projet = "villa"
        elif "appartement" in txt or "appart" in txt:
            type_projet = "appartement"
        else:
            type_projet = "construction"

        infos_ok = terrain is not None and (chambres + salons + cuisines + sdb) > 0

        return {
            "terrain_m2":        terrain,
            "type_projet":       type_projet,
            "pieces": {
                "chambres":        chambres,
                "salons":          salons,
                "cuisines":        cuisines,
                "salles_de_bain":  sdb,
                "wc":              wc,
                "jardin":          jardin,
                "piscine":         piscine,
                "dressing":        dressing,
            },
            "qualite":           "standard",
            "infos_suffisantes": infos_ok,
        }

    # ── Demande de précisions ─────────────────────────────────────────────────

    def _ask_clarification(self, message: str, projet: dict) -> str:
        manquants = []
        if not projet.get("terrain_m2"):
            manquants.append("la surface du terrain (en m²)")
        pieces = projet.get("pieces", {})
        if not any([pieces.get("chambres"), pieces.get("salons"),
                    pieces.get("cuisines"), pieces.get("salles_de_bain")]):
            manquants.append("les pièces souhaitées (chambres, salon, cuisine...)")

        if manquants:
            return (
                "Pour établir votre devis, j'ai besoin de quelques informations supplémentaires.\n\n"
                f"Pourriez-vous me préciser : **{' et '.join(manquants)}** ?"
            )

        try:
            msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + self.history
            response = ollama.chat(
                model=self.model,
                messages=msgs,
                options={"temperature": 0.3, "num_predict": 200},
            )
            return response["message"]["content"].strip()
        except Exception:
            return (
                "Pourriez-vous me préciser la surface de votre terrain (m²) "
                "et les pièces que vous souhaitez ?"
            )

    # ── Calcul du devis ───────────────────────────────────────────────────────

    def _compute_devis(self, projet: dict) -> dict:
        terrain_m2  = float(projet["terrain_m2"])
        pieces_raw  = projet.get("pieces", {})

        # ── Normalisation du type_projet ──────────────────────────────────────
        # Le LLM peut retourner des valeurs non prévues ("maison", "villa",
        # "house"…). On normalise vers les 5 modes valides.
        _raw_type = str(projet.get("type_projet", "construction")).lower().strip()
        _TYPE_NORM = {
            "construction": "construction", "maison":        "construction",
            "house":        "construction", "neuf":          "construction",
            "neuve":        "construction", "villa":         "villa",
            "duplex":       "villa",        "renovation":    "renovation",
            "rénovation":   "renovation",   "renov":         "renovation",
            "cafe_commerce":"cafe_commerce","cafe":          "cafe_commerce",
            "commerce":     "cafe_commerce","restaurant":    "cafe_commerce",
            "appartement":  "appartement",  "appart":        "appartement",
            "studio":       "appartement",
        }
        type_projet = _TYPE_NORM.get(_raw_type, "construction")

        def _int(val, default=0):
            try:
                return int(val) if val is not None else default
            except (TypeError, ValueError):
                return default

        # ── Extraction des pièces avec double sécurité ────────────────────────
        # Si le LLM a raté piscine/jardin, on relit le message original
        _msg = self.history[-1]["content"].lower() if self.history else ""
        _jardin  = bool(pieces_raw.get("jardin")  or False) or "jardin"  in _msg
        _piscine = bool(pieces_raw.get("piscine") or False) or "piscine" in _msg

        pieces = {
            "chambres":      _int(pieces_raw.get("chambres"), 0),
            "salons":        _int(pieces_raw.get("salons"), 1),
            "cuisines":      _int(pieces_raw.get("cuisines"), 1),
            "salle_de_bain": _int(pieces_raw.get("salles_de_bain"), 1),
            "wc":            _int(pieces_raw.get("wc"), 1),
            "jardin":        _jardin,
            "piscine":       _piscine,
            "dressing":      bool(pieces_raw.get("dressing") or pieces_raw.get("chambres", 0) > 0),
        }

        description = self._build_description(type_projet, pieces)

        rag_prices = self.retriever.get_prices_for_project(description)
        if "_meta" not in rag_prices:
            rag_prices["_meta"] = {}
        rag_prices["_meta"]["mode"] = type_projet

        surfaces = self.calculator.estimate_surfaces(terrain_m2, pieces)
        devis = self.calculator.build_devis(surfaces, rag_prices, pieces)
        devis["_meta"] = rag_prices.get("_meta", {})

        return devis

    def _build_description(self, type_projet: str, pieces: dict) -> str:
        type_map = {
            "renovation":    "rénovation maison",
            "cafe_commerce": "café commerce local commercial",
            "villa":         "villa construction",
            "appartement":   "appartement construction",
            "construction":  "construction maison",
        }
        base = type_map.get(type_projet, "construction maison")
        parts = [base]
        if pieces.get("chambres"):
            parts.append(f"{pieces['chambres']} chambres")
        if pieces.get("salons"):
            parts.append("salon")
        if pieces.get("cuisines"):
            parts.append("cuisine")
        if pieces.get("salle_de_bain"):
            parts.append("salle de bain")
        if pieces.get("jardin"):
            parts.append("jardin")
        if pieces.get("piscine"):
            parts.append("piscine")
        if pieces.get("dressing"):
            parts.append("dressing placard")
        return " ".join(parts)

    # ── Formatage de la réponse texte ─────────────────────────────────────────

    def _format_devis_text(self, devis: dict, projet: dict) -> str:
        resume  = devis.get("resume", {})
        postes  = devis.get("postes", {})
        total   = devis.get("total", {})
        acc     = devis.get("accuracy", {})

        terrain  = resume.get("terrain", "?")
        surf_hab = resume.get("surface_habitable", "?")
        surf_jrd = resume.get("surface_jardin", "0 m²")
        surf_all = resume.get("surface_allee", "0 m²")
        surf_pis = resume.get("surface_piscine", "")

        t_min = total.get("total_min_str", "—")
        t_mid = total.get("total_mid_str", "—")
        t_max = total.get("total_max_str", "—")

        acc_score   = acc.get("score", 0)
        acc_qualite = acc.get("qualite", "")
        acc_detail  = acc.get("detail", "")
        nb_ds       = acc.get("postes_dataset", 0)
        nb_tot      = acc.get("postes_total", 0)

        # En-tête
        header_parts = [
            f"**Terrain :** {terrain}",
            f"**Surface habitable :** {surf_hab}",
            f"**Jardin :** {surf_jrd}",
        ]
        if surf_pis:
            header_parts.append(f"**Piscine :** {surf_pis}")
        header_parts.append(f"**Allée/parking :** {surf_all}")

        lines = [
            "## 🏗️ Devis Construction — Tunisie 2025",
            "",
            "  &nbsp;|&nbsp;  ".join(header_parts),
            "",
        ]

        lines.append("| # | Poste de travaux | Qté | MIN (DT) | MOY (DT) | MAX (DT) |")
        lines.append("|:-:|:----------------|:---:|--------:|--------:|--------:|")

        ICONS = {
            "gros_oeuvre":        "🏛️",
            "carrelage_sol":      "🪨",
            "faience":            "🔷",
            "isolation":          "🧱",
            "peinture":           "🖌️",
            "electricite":        "⚡",
            "plomberie":          "🚰",
            "fenetre":            "🪟",
            "porte_fenetre":      "🚪",
            "porte_blindee":      "🔒",
            "porte_interieure":   "🚪",
            "portes_interieures": "🚪",
            "cuisine_equipee":    "🍳",
            "salle_de_bain":      "🚿",
            "chauffe_eau":        "🌡️",
            "climatisation":      "❄️",
            "dressing":           "👔",
            "raccord_eau":        "💧",
            "raccord_gaz":        "🔥",
            "raccord_elec":       "🔌",
            "securite":           "🔐",
            "jardin":             "🌿",
            "piscine":            "🏊",
            "faux_plafond":       "🏠",
            "fenetres":           "🪟",
        }

        def _fmt(v):
            try:
                return f"{int(round(float(v))):,}".replace(",", "\u202f")
            except Exception:
                return str(v)

        for i, (key, p) in enumerate(postes.items(), 1):
            icon  = ICONS.get(key, "🔧")
            desc  = p.get("description", key)
            qte   = p.get("quantite", 1)
            unite = p.get("unite", "")
            c_min = _fmt(p.get("cout_min", 0))
            c_mid = _fmt(p.get("cout_mid", 0))
            c_max = _fmt(p.get("cout_max", 0))
            qte_str = f"{qte} {unite}" if unite else str(qte)
            lines.append(
                f"| {i} | {icon} {desc} | {qte_str} | {c_min} | {c_mid} | {c_max} |"
            )

        lines.append(
            f"| | **💰 TOTAL** *(imprévus 10% inclus)* | | "
            f"**{t_min}** | **{t_mid}** | **{t_max}** |"
        )

        lines += [
            "",
            "---",
            f"### 💰 Fourchette totale : **{t_min} → {t_max}**",
            f"*(Estimation moyenne recommandée : **{t_mid}**)*",
            "",
            "---",
            "**Légende qualité :**",
            "",
            "| Niveau | Description |",
            "|:------:|:------------|",
            "| **MIN** | Matériaux économiques, main-d'œuvre standard |",
            "| **MOY** | Qualité intermédiaire — *recommandée* |",
            "| **MAX** | Matériaux premium, finitions haut de gamme |",
            "",
            "---",
            f"### 🎯 Précision du devis : {acc_qualite} — **{acc_score}%**",
            f"*{nb_ds} sur {nb_tot} postes calculés directement depuis le dataset de prix tunisien.*",
            f"> {acc_detail}",
            "",
            "> ⚠️ *Hors honoraires architecte (5–8% du total) et taxes.*",
        ]

        return "\n".join(lines)

    # ── Réinitialisation ──────────────────────────────────────────────────────

    def reset(self):
        self.history = []