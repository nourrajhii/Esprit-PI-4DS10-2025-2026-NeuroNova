"""
geo_data.py
Données géographiques à 3 niveaux : gouvernorat → ville → standing.
Coefficients des attributs du bien et services de proximité.
"""

# ── Coefficients de standing ───────────────────────────────────────────────────
STANDING_COEFFS: dict[str, float] = {
    "populaire":     0.75,
    "intermédiaire": 1.00,
    "résidentiel":   1.30,
    "luxe":          1.70,
    "vue_mer":       1.50,
}

STANDINGS = list(STANDING_COEFFS.keys())

# ── Attributs du bien — coefficients cumulatifs ───────────────────────────────
ATTRIBUTS_VENTE: dict[str, float] = {
    "garage":    0.06,
    "piscine":   0.10,
    "sous_sol":  0.05,
    "terrasse":  0.07,
    "ascenseur": 0.04,
    "vue_mer":   0.18,
    "jardin":    0.08,
}

ATTRIBUTS_LOCATION: dict[str, float] = {
    "garage":      0.08,
    "piscine":     0.12,
    "ascenseur":   0.05,
    "terrasse":    0.06,
    "meuble":      0.15,
    "clim":        0.07,
    "gardiennage": 0.05,
    "vue_mer":     0.20,
}

# ── Services de proximité — coefficients ──────────────────────────────────────
SERVICES_PROXIMITE: dict[str, float] = {
    "supermarche": 0.03,
    "pharmacie":   0.02,
    "ecole":       0.04,
    "transport":   0.05,
    "restaurant":  0.01,
    "hopital":     0.03,
    "mosquee":     0.01,
    "parc":        0.03,
}

SERVICES_LABELS: dict[str, str] = {
    "supermarche": "Supermarché / Épicerie",
    "pharmacie":   "Pharmacie",
    "ecole":       "École / Lycée",
    "transport":   "Transport en commun",
    "restaurant":  "Café / Restaurant",
    "hopital":     "Hôpital / Clinique",
    "mosquee":     "Mosquée",
    "parc":        "Parc / Espace vert",
}

# ── Coordonnées des villes (lat, lng) ─────────────────────────────────────────
COORDS_VILLES: dict[str, tuple[float, float]] = {
    # Grand Tunis — Tunis
    "Tunis Centre":       (36.8065, 10.1815),
    "La Marsa":           (36.8789, 10.3249),
    "Carthage":           (36.8528, 10.3233),
    "Le Bardo":           (36.8092, 10.1486),
    "Cité El Khadra":     (36.8284, 10.2106),
    "El Menzah":          (36.8473, 10.2047),
    "El Manar":           (36.8421, 10.2156),
    "Les Berges du Lac":  (36.8329, 10.2425),
    "Montplaisir":        (36.8221, 10.1903),
    "El Aouina":          (36.8439, 10.2306),
    "Sidi Bou Saïd":      (36.8712, 10.3418),
    "La Goulette":        (36.8185, 10.3055),
    "Bab El Bhar":        (36.7998, 10.1765),
    "Menzah 6":           (36.8512, 10.2078),
    "Ennasr 2":           (36.8590, 10.2234),
    # Grand Tunis — Ariana
    "Ariana Ville":       (36.8655, 10.1928),
    "La Soukra":          (36.8935, 10.2304),
    "Ennasr":             (36.8578, 10.2198),
    "Riadh Andalous":     (36.8721, 10.2156),
    "Borj Louzir":        (36.8621, 10.2356),
    "Ettadhamen":         (36.8342, 10.1589),
    "Mnihla":             (36.8756, 10.1712),
    "Kalâat El Andalous": (36.9434, 10.0896),
    # Grand Tunis — Ben Arous
    "Ben Arous Centre":   (36.7533, 10.2314),
    "El Mourouj":         (36.7801, 10.2156),
    "Megrine":            (36.7684, 10.2198),
    "Hammam Lif":         (36.7296, 10.3361),
    "Ezzahra":            (36.7456, 10.3165),
    "Radès":              (36.7731, 10.2867),
    "Bou Mhel":           (36.7519, 10.2448),
    "Fouchana":           (36.7007, 10.1671),
    "Mornag":             (36.6783, 10.2728),
    # Grand Tunis — Manouba
    "Manouba Ville":      (36.8086, 10.0994),
    "Oued Ellil":         (36.8267, 10.0603),
    "Tebourba":           (36.8330,  9.8398),
    "Jedaida":            (36.8502,  9.9161),
    "Den Den":            (36.8219, 10.1481),
    "Douar Hicher":       (36.8189, 10.1278),
    "El Battan":          (36.8445,  9.9872),
    # Nabeul
    "Nabeul Ville":       (36.4511, 10.7381),
    "Hammamet":           (36.3992, 10.6267),
    "Kélibia":            (36.8496, 11.1014),
    "Grombalia":          (36.6007, 10.5064),
    "Beni Khiar":         (36.4754, 10.7842),
    "Menzel Temime":      (36.7844, 10.9891),
    "Soliman":            (36.6992, 10.4753),
    "Hammamet Nord":      (36.4300, 10.6150),
    # Zaghouan
    "Zaghouan Ville":     (36.4025, 10.1428),
    "Zriba":              (36.4278, 10.2012),
    "El Fahs":            (36.3726, 10.0101),
    "Nadhour":            (36.1982,  9.9851),
    # Bizerte
    "Bizerte Centre":     (37.2744,  9.8739),
    "Menzel Bourguiba":   (37.1584,  9.7961),
    "Menzel Jemil":       (37.2214,  9.8223),
    "Ras Jebel":          (37.2262,  9.9721),
    "El Alia":            (37.1736,  9.9345),
    "Tinja":              (37.1427,  9.7134),
    # Béja
    "Béja Ville":         (36.7258,  9.1817),
    "Medjez El Bab":      (36.6426,  9.6098),
    "Testour":            (36.5494,  9.4526),
    "Nefza":              (37.0276,  9.0213),
    "Thibar":             (36.7286,  9.3172),
    # Jendouba
    "Jendouba Ville":     (36.5013,  8.7803),
    "Bousalem":           (36.6208,  8.9740),
    "Tabarka":            (36.9544,  8.7588),
    "Aïn Draham":         (36.7838,  8.6862),
    "Ghardimaou":         (36.4488,  8.4338),
    # Kef
    "Kef Ville":          (36.1826,  8.7145),
    "Sers":               (36.0757,  8.5698),
    "Tajerouine":         (35.8927,  8.5548),
    "Dahmani":            (36.0443,  8.8290),
    "Kalaa Khasba":       (35.9734,  8.6551),
    # Siliana
    "Siliana Ville":      (36.0851,  9.3702),
    "Bourouis":           (36.5745,  9.5612),
    "Krib":               (36.2690,  9.4784),
    "Makthar":            (35.8581,  9.2059),
    "Rohia":              (35.9645,  9.5028),
    # Sousse
    "Sousse Centre":      (35.8283, 10.6361),
    "Hammam Sousse":      (35.8606, 10.5969),
    "Chott Mariem":       (35.9006, 10.5527),
    "Akouda":             (35.8726, 10.5733),
    "Kalaa Kebira":       (35.9428, 10.5351),
    "Kalaa Sghira":       (35.8945, 10.5654),
    "M'Saken":            (35.7287, 10.5701),
    "Hergla":             (36.0548, 10.5184),
    # Monastir
    "Monastir Centre":    (35.7643, 10.8113),
    "Skanes":             (35.7814, 10.7573),
    "Dkhila":             (35.7906, 10.8246),
    "Ksar Hellal":        (35.6449, 10.8901),
    "Téboulba":           (35.7027, 10.9357),
    "Jemmal":             (35.6226, 10.7580),
    "Bembla":             (35.7351, 10.8756),
    "Ouerdanine":         (35.6509, 10.7946),
    # Mahdia
    "Mahdia Ville":       (35.5047, 11.0622),
    "El Jem":             (35.2975, 10.7138),
    "Ksour Essef":        (35.4263, 11.0001),
    "Chebba":             (35.2424, 11.1142),
    "Bou Merdes":         (35.6424, 10.9145),
    "Melloulech":         (35.3989, 10.9287),
    # Sfax
    "Sfax Centre":        (34.7406, 10.7603),
    "Sfax Nord":          (34.7650, 10.7450),
    "Sfax Sud":           (34.7200, 10.7800),
    "Sakiet Ezzit":       (34.7800, 10.7200),
    "El Ain":             (34.8287, 10.7087),
    "Bir Ali Ben Khalifa":(34.7194, 10.0962),
    "Thyna":              (34.6784, 10.7367),
    "Agareb":             (34.7453, 10.5323),
    # Kairouan
    "Kairouan Ville":     (35.6781, 10.0972),
    "El Alaa":            (35.5634, 10.1012),
    "Sbikha":             (35.9087, 10.0284),
    "Oueslatia":          (36.0284, 10.0044),
    "Haffouz":            (35.6337,  9.6720),
    "Nasrallah":          (35.7126,  9.9748),
    # Kasserine
    "Kasserine Ville":    (35.1677,  8.8305),
    "Sbeitla":            (35.2392,  9.1288),
    "Thala":              (35.5791,  8.6783),
    "Fériana":            (35.0062,  8.5687),
    "Majel Bel Abbès":    (35.3254,  8.7234),
    "Ezzouhour":          (35.2095,  8.9156),
    # Sidi Bouzid
    "Sidi Bouzid Ville":  (35.0380,  9.4849),
    "Regueb":             (34.9109,  9.7988),
    "Sidi Ali Ben Aoun":  (35.1726,  9.6452),
    "Menzel Bouzaiane":   (34.8770,  9.4823),
    "El Meknassy":        (34.9987,  9.6312),
    # Gabès
    "Gabès Ville":        (33.8815, 10.0982),
    "Gabès Sud":          (33.8600, 10.1200),
    "Gabès Ouest":        (33.8900, 10.0700),
    "El Hamma":           (33.8897,  9.7984),
    "Mareth":             (33.6551, 10.2971),
    "Matmata":            (33.5454,  9.9637),
    # Medenine
    "Medenine Ville":     (33.3550, 10.4953),
    "Houmt Souk":         (33.8761, 10.8573),
    "Midoun":             (33.8192, 10.9942),
    "Zarzis":             (33.5038, 11.1120),
    "Ben Guerdane":       (33.1409, 11.2199),
    "Djerba Nord":        (33.9050, 10.9100),
    "Beni Kheddache":     (33.2878, 10.2864),
    # Tataouine
    "Tataouine Ville":    (32.9298, 10.4519),
    "Ghomrassen":         (33.0567, 10.2025),
    "Remada":             (32.3128, 10.3988),
    "Bir Lahmar":         (32.7601, 10.2456),
    "Smar":               (32.7012, 10.5234),
    # Gafsa
    "Gafsa Ville":        (34.4256,  8.7844),
    "Gafsa Nord":         (34.4450,  8.7600),
    "El Ksar":            (34.4100,  8.7950),
    "Oum El Araies":      (34.8823,  8.4943),
    "Métlaoui":           (34.3269,  8.3903),
    "Redeyef":            (34.3860,  8.2002),
    # Tozeur
    "Tozeur Ville":       (33.9197,  8.1335),
    "Nefta":              (33.8728,  7.8782),
    "Degache":            (33.9748,  8.2122),
    "Tameghza":           (34.1617,  7.8834),
    "Hazoua":             (33.6853,  8.0198),
    # Kébili
    "Kébili Ville":       (33.7047,  8.9652),
    "Douz":               (33.4557,  9.0207),
    "Souk El Ahed":       (33.7834,  9.0451),
    "Faouar":             (33.2356,  9.0456),
}

# ── Villes par gouvernorat ────────────────────────────────────────────────────
VILLES_PAR_GOUVERNORAT: dict[str, list[str]] = {
    "Tunis":       ["Tunis Centre", "La Marsa", "Carthage", "Le Bardo", "Cité El Khadra",
                    "El Menzah", "El Manar", "Les Berges du Lac", "Montplaisir", "El Aouina",
                    "Sidi Bou Saïd", "La Goulette", "Bab El Bhar", "Menzah 6", "Ennasr 2"],
    "Ariana":      ["Ariana Ville", "La Soukra", "Ennasr", "Riadh Andalous",
                    "Borj Louzir", "Ettadhamen", "Mnihla", "Kalâat El Andalous"],
    "Ben Arous":   ["Ben Arous Centre", "El Mourouj", "Megrine", "Hammam Lif",
                    "Ezzahra", "Radès", "Bou Mhel", "Fouchana", "Mornag"],
    "Manouba":     ["Manouba Ville", "Oued Ellil", "Tebourba", "Jedaida",
                    "Den Den", "Douar Hicher", "El Battan"],
    "Nabeul":      ["Nabeul Ville", "Hammamet", "Kélibia", "Grombalia",
                    "Beni Khiar", "Menzel Temime", "Soliman", "Hammamet Nord"],
    "Zaghouan":    ["Zaghouan Ville", "Zriba", "El Fahs", "Nadhour"],
    "Bizerte":     ["Bizerte Centre", "Menzel Bourguiba", "Menzel Jemil",
                    "Ras Jebel", "El Alia", "Tinja"],
    "Béja":        ["Béja Ville", "Medjez El Bab", "Testour", "Nefza", "Thibar"],
    "Jendouba":    ["Jendouba Ville", "Bousalem", "Tabarka", "Aïn Draham", "Ghardimaou"],
    "Kef":         ["Kef Ville", "Sers", "Tajerouine", "Dahmani", "Kalaa Khasba"],
    "Siliana":     ["Siliana Ville", "Bourouis", "Krib", "Makthar", "Rohia"],
    "Sousse":      ["Sousse Centre", "Hammam Sousse", "Chott Mariem", "Akouda",
                    "Kalaa Kebira", "Kalaa Sghira", "M'Saken", "Hergla"],
    "Monastir":    ["Monastir Centre", "Skanes", "Dkhila", "Ksar Hellal",
                    "Téboulba", "Jemmal", "Bembla", "Ouerdanine"],
    "Mahdia":      ["Mahdia Ville", "El Jem", "Ksour Essef", "Chebba",
                    "Bou Merdes", "Melloulech"],
    "Sfax":        ["Sfax Centre", "Sfax Nord", "Sfax Sud", "Sakiet Ezzit",
                    "El Ain", "Bir Ali Ben Khalifa", "Thyna", "Agareb"],
    "Kairouan":    ["Kairouan Ville", "El Alaa", "Sbikha", "Oueslatia", "Haffouz", "Nasrallah"],
    "Kasserine":   ["Kasserine Ville", "Sbeitla", "Thala", "Fériana",
                    "Majel Bel Abbès", "Ezzouhour"],
    "Sidi Bouzid": ["Sidi Bouzid Ville", "Regueb", "Sidi Ali Ben Aoun",
                    "Menzel Bouzaiane", "El Meknassy"],
    "Gabès":       ["Gabès Ville", "Gabès Sud", "Gabès Ouest", "El Hamma", "Mareth", "Matmata"],
    "Medenine":    ["Medenine Ville", "Houmt Souk", "Midoun", "Zarzis",
                    "Ben Guerdane", "Djerba Nord", "Beni Kheddache"],
    "Tataouine":   ["Tataouine Ville", "Ghomrassen", "Remada", "Bir Lahmar", "Smar"],
    "Gafsa":       ["Gafsa Ville", "Gafsa Nord", "El Ksar", "Oum El Araies", "Métlaoui", "Redeyef"],
    "Tozeur":      ["Tozeur Ville", "Nefta", "Degache", "Tameghza", "Hazoua"],
    "Kébili":      ["Kébili Ville", "Douz", "Souk El Ahed", "Faouar"],
}


# ── Utilitaires ───────────────────────────────────────────────────────────────

def get_coords(ville: str, gouvernorat: str) -> tuple[float, float] | None:
    """Retourne (lat, lng) d'une ville, ou le centre du gouvernorat, ou None."""
    if ville in COORDS_VILLES:
        return COORDS_VILLES[ville]
    for v in VILLES_PAR_GOUVERNORAT.get(gouvernorat, []):
        if v in COORDS_VILLES:
            return COORDS_VILLES[v]
    return None


def calc_score_attributs(mode: str, attributs: list[str]) -> dict[str, float]:
    """Retourne {attr: coeff} pour les attributs actifs du bien."""
    ref = ATTRIBUTS_VENTE if mode == "vente" else ATTRIBUTS_LOCATION
    return {a: ref[a] for a in attributs if a in ref}


def calc_score_proximite(services: list[str]) -> dict[str, float]:
    """Retourne {service: coeff} pour les services détectés autour du bien."""
    return {s: SERVICES_PROXIMITE[s] for s in services if s in SERVICES_PROXIMITE}
