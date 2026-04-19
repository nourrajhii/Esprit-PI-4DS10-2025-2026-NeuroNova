"""
market_data.py
Profils de marché pour les 24 gouvernorats tunisiens.
Données calibrées sur les tendances 2022-2025 du marché immobilier tunisien.
"""

GOUVERNORATS: dict[str, dict] = {

    # ── Grand Tunis ───────────────────────────────────────────────────────────
    "Tunis": {
        "taux_vente_mensuel": 0.0065,
        "taux_location_mensuel": 0.0048,
        "prix_moyen_m2": {
            "appartement": 3500, "villa": 5800, "maison": 2900,
            "terrain": 1500, "bureau": 3200,
        },
        "loyers_moyens": {"S+1": 900, "S+2": 1350, "S+3": 1800, "S+4": 2500},
        "tension": "très haute",
        "risque": "faible",
        "volatilite": 0.038,
        "description": (
            "Capitale économique et administrative, Tunis concentre la plus forte "
            "demande immobilière du pays. Le marché est porté par la diaspora, "
            "les cadres supérieurs et la proximité des pôles d'emploi. "
            "L'offre reste structurellement inférieure à la demande, ce qui maintient "
            "une pression haussière durable sur les prix."
        ),
        "facteurs": ["Demande diaspora forte", "Pôles d'emploi denses", "Offre limitée", "Projets urbains actifs"],
    },
    "Ariana": {
        "taux_vente_mensuel": 0.0060,
        "taux_location_mensuel": 0.0045,
        "prix_moyen_m2": {
            "appartement": 3100, "villa": 5000, "maison": 2600,
            "terrain": 1300, "bureau": 2800,
        },
        "loyers_moyens": {"S+1": 780, "S+2": 1150, "S+3": 1550, "S+4": 2100},
        "tension": "haute",
        "risque": "faible",
        "volatilite": 0.035,
        "description": (
            "Gouvernorat résidentiel prisé du Grand Tunis, Ariana bénéficie de la "
            "proximité de l'aéroport international et des zones d'affaires. "
            "Les quartiers modernes de La Soukra, Ennasr et Borj Louzir attirent "
            "une clientèle aisée. Le marché reste dynamique avec une croissance "
            "régulière soutenue par de nouveaux projets résidentiels."
        ),
        "facteurs": ["Proximité aéroport Tunis-Carthage", "Zones résidentielles modernes", "Croissance démographique soutenue"],
    },
    "Ben Arous": {
        "taux_vente_mensuel": 0.0055,
        "taux_location_mensuel": 0.0042,
        "prix_moyen_m2": {
            "appartement": 2800, "villa": 4500, "maison": 2400,
            "terrain": 1100, "bureau": 2500,
        },
        "loyers_moyens": {"S+1": 700, "S+2": 1050, "S+3": 1400, "S+4": 1900},
        "tension": "haute",
        "risque": "faible",
        "volatilite": 0.032,
        "description": (
            "Gouvernorat industriel et résidentiel au sud du Grand Tunis, "
            "Ben Arous combine zones industrielles de Megrine, El Mourouj et "
            "quartiers résidentiels à prix accessibles. La demande locative est "
            "portée par les travailleurs du bassin industriel et les étudiants "
            "des universités privées."
        ),
        "facteurs": ["Bassin industriel dense", "Prix accessibles vs Tunis", "Bonne connectivité routière"],
    },
    "Manouba": {
        "taux_vente_mensuel": 0.0050,
        "taux_location_mensuel": 0.0038,
        "prix_moyen_m2": {
            "appartement": 2500, "villa": 4000, "maison": 2200,
            "terrain": 900, "bureau": 2200,
        },
        "loyers_moyens": {"S+1": 620, "S+2": 920, "S+3": 1250, "S+4": 1650},
        "tension": "modérée",
        "risque": "faible",
        "volatilite": 0.032,
        "description": (
            "Gouvernorat périurbain à l'ouest du Grand Tunis, Manouba offre des "
            "prix attractifs pour les primo-accédants. L'amélioration des "
            "infrastructures de transport (RFR, autoroutes) renforce son attractivité "
            "et stimule progressivement la demande immobilière dans les communes "
            "de Oued Ellil, Tebourba et Jedaida."
        ),
        "facteurs": ["Prix abordables pour primo-accédants", "Amélioration infrastructure transport", "Pression périurbaine croissante"],
    },

    # ── Cap Bon & Nord ────────────────────────────────────────────────────────
    "Nabeul": {
        "taux_vente_mensuel": 0.0062,
        "taux_location_mensuel": 0.0052,
        "prix_moyen_m2": {
            "appartement": 3200, "villa": 5200, "maison": 2700,
            "terrain": 1400, "bureau": 2600,
        },
        "loyers_moyens": {"S+1": 850, "S+2": 1250, "S+3": 1650, "S+4": 2200},
        "tension": "haute",
        "risque": "modéré",
        "volatilite": 0.050,
        "description": (
            "Le Cap Bon est l'une des destinations immobilières les plus prisées "
            "de Tunisie. Hammamet, Nabeul et Kélibia attirent la clientèle "
            "touristique internationale et les résidences secondaires de la "
            "diaspora. Le marché présente une saisonnalité marquée mais la "
            "demande résidentielle permanente progresse régulièrement."
        ),
        "facteurs": ["Hub touristique méditerranéen", "Résidences secondaires diaspora", "Saisonnalité forte", "Littoral valorisé"],
    },
    "Zaghouan": {
        "taux_vente_mensuel": 0.0038,
        "taux_location_mensuel": 0.0028,
        "prix_moyen_m2": {
            "appartement": 1800, "villa": 2900, "maison": 1600,
            "terrain": 650, "bureau": 1500,
        },
        "loyers_moyens": {"S+1": 450, "S+2": 650, "S+3": 850, "S+4": 1100},
        "tension": "faible",
        "risque": "modéré",
        "volatilite": 0.042,
        "description": (
            "Gouvernorat rural proche de Tunis, Zaghouan reste peu urbanisé. "
            "Le marché immobilier est en légère progression grâce à la proximité "
            "de la capitale et au développement de zones industrielles sur l'axe "
            "Tunis-Zaghouan. Le potentiel d'appréciation reste lié aux "
            "investissements infrastructurels futurs."
        ),
        "facteurs": ["Proximité Tunis (60 km)", "Développement zones industrielles", "Marché émergent à potentiel"],
    },
    "Bizerte": {
        "taux_vente_mensuel": 0.0048,
        "taux_location_mensuel": 0.0036,
        "prix_moyen_m2": {
            "appartement": 2400, "villa": 3800, "maison": 2100,
            "terrain": 1000, "bureau": 2000,
        },
        "loyers_moyens": {"S+1": 600, "S+2": 900, "S+3": 1200, "S+4": 1600},
        "tension": "modérée",
        "risque": "modéré",
        "volatilite": 0.040,
        "description": (
            "Ville portuaire et industrielle du nord, Bizerte dispose d'un marché "
            "immobilier stable. La zone industrielle de Menzel Bourguiba génère "
            "une demande locative constante. Le front de mer (Cap Blanc, "
            "Corniche) attire également les résidences secondaires et les "
            "projets hôteliers."
        ),
        "facteurs": ["Zone industrielle stratégique", "Potentiel balnéaire sous-exploité", "Port militaire et commercial"],
    },

    # ── Nord-Ouest ────────────────────────────────────────────────────────────
    "Béja": {
        "taux_vente_mensuel": 0.0030,
        "taux_location_mensuel": 0.0022,
        "prix_moyen_m2": {
            "appartement": 1600, "villa": 2600, "maison": 1400,
            "terrain": 550, "bureau": 1300,
        },
        "loyers_moyens": {"S+1": 380, "S+2": 560, "S+3": 750, "S+4": 980},
        "tension": "faible",
        "risque": "élevé",
        "volatilite": 0.060,
        "description": (
            "Gouvernorat agricole du nord-ouest, Béja est dominé par la "
            "céréaliculture et l'élevage. Le marché immobilier y est peu actif, "
            "avec des prix parmi les plus abordables du pays. La demande provient "
            "principalement des fonctionnaires, agriculteurs et étudiants de "
            "l'Université de Béja."
        ),
        "facteurs": ["Économie agricole dominante", "Faible urbanisation", "Exode rural vers Tunis"],
    },
    "Jendouba": {
        "taux_vente_mensuel": 0.0025,
        "taux_location_mensuel": 0.0020,
        "prix_moyen_m2": {
            "appartement": 1400, "villa": 2200, "maison": 1200,
            "terrain": 480, "bureau": 1100,
        },
        "loyers_moyens": {"S+1": 340, "S+2": 490, "S+3": 660, "S+4": 860},
        "tension": "très faible",
        "risque": "élevé",
        "volatilite": 0.070,
        "description": (
            "Gouvernorat frontalier avec l'Algérie, Jendouba dispose d'un marché "
            "immobilier très peu actif. Les échanges sont limités et les prix "
            "restent très accessibles. La proximité du parc national de Aïn "
            "Draham offre un potentiel écotouristique encore sous-exploité "
            "qui pourrait stimuler la demande future."
        ),
        "facteurs": ["Zone frontalière Algérie", "Très faible demande formelle", "Potentiel écotouristique"],
    },
    "Kef": {
        "taux_vente_mensuel": 0.0022,
        "taux_location_mensuel": 0.0018,
        "prix_moyen_m2": {
            "appartement": 1300, "villa": 2000, "maison": 1100,
            "terrain": 420, "bureau": 1000,
        },
        "loyers_moyens": {"S+1": 320, "S+2": 460, "S+3": 620, "S+4": 810},
        "tension": "très faible",
        "risque": "élevé",
        "volatilite": 0.072,
        "description": (
            "Chef-lieu de gouvernorat du nord-ouest montagneux, Le Kef est une "
            "ville à vocation administrative et militaire. Le marché immobilier "
            "est atone, avec peu de transactions et des prix stagnants. La "
            "ville de Sers abrite quelques projets miniers qui génèrent une "
            "demande locative limitée."
        ),
        "facteurs": ["Économie atone", "Exode des jeunes vers Tunis et Sousse", "Marché quasi-inactif"],
    },
    "Siliana": {
        "taux_vente_mensuel": 0.0020,
        "taux_location_mensuel": 0.0016,
        "prix_moyen_m2": {
            "appartement": 1200, "villa": 1900, "maison": 1050,
            "terrain": 400, "bureau": 950,
        },
        "loyers_moyens": {"S+1": 300, "S+2": 430, "S+3": 580, "S+4": 750},
        "tension": "très faible",
        "risque": "élevé",
        "volatilite": 0.080,
        "description": (
            "L'un des gouvernorats les moins urbanisés de Tunisie, Siliana est "
            "caractérisé par une économie essentiellement rurale et minière. "
            "Le marché immobilier formel est quasi-inexistant, avec des "
            "transactions très sporadiques et des prix parmi les plus bas "
            "du pays."
        ),
        "facteurs": ["Économie minière et agricole", "Faible population urbaine", "Marché stagnant"],
    },

    # ── Centre-Est (Sahel) ────────────────────────────────────────────────────
    "Sousse": {
        "taux_vente_mensuel": 0.0060,
        "taux_location_mensuel": 0.0050,
        "prix_moyen_m2": {
            "appartement": 3000, "villa": 4800, "maison": 2600,
            "terrain": 1300, "bureau": 2700,
        },
        "loyers_moyens": {"S+1": 780, "S+2": 1150, "S+3": 1550, "S+4": 2050},
        "tension": "haute",
        "risque": "faible",
        "volatilite": 0.038,
        "description": (
            "Troisième ville de Tunisie et capitale du Sahel, Sousse est un hub "
            "économique, touristique et universitaire. Le marché immobilier y est "
            "très actif, porté par le tourisme international, les étudiants et "
            "une diaspora importante. Les projets hôteliers et résidentiels "
            "se multiplient sur la zone côtière."
        ),
        "facteurs": ["Hub touristique de premier rang", "Ville universitaire dynamique", "Diaspora très active", "Projets côtiers"],
    },
    "Monastir": {
        "taux_vente_mensuel": 0.0058,
        "taux_location_mensuel": 0.0048,
        "prix_moyen_m2": {
            "appartement": 2900, "villa": 4700, "maison": 2500,
            "terrain": 1250, "bureau": 2600,
        },
        "loyers_moyens": {"S+1": 750, "S+2": 1100, "S+3": 1480, "S+4": 1950},
        "tension": "haute",
        "risque": "faible",
        "volatilite": 0.040,
        "description": (
            "Ville natale de Bourguiba, Monastir bénéficie d'une très forte "
            "demande de la diaspora tunisienne établie à l'étranger. L'aéroport "
            "international Habib Bourguiba et les zones résidentielles balnéaires "
            "de Skanes et Dkhila soutiennent un marché immobilier premium qui "
            "résiste bien aux cycles économiques."
        ),
        "facteurs": ["Très forte demande diaspora", "Aéroport international direct", "Prestige balnéaire reconnu"],
    },
    "Mahdia": {
        "taux_vente_mensuel": 0.0045,
        "taux_location_mensuel": 0.0038,
        "prix_moyen_m2": {
            "appartement": 2200, "villa": 3600, "maison": 1900,
            "terrain": 950, "bureau": 2000,
        },
        "loyers_moyens": {"S+1": 560, "S+2": 820, "S+3": 1100, "S+4": 1450},
        "tension": "modérée",
        "risque": "modéré",
        "volatilite": 0.048,
        "description": (
            "Gouvernorat côtier du Sahel, Mahdia combine une économie de pêche "
            "traditionnelle et un tourisme en plein développement. Les communes "
            "côtières attirent des investisseurs recherchant des biens plus "
            "abordables que Sousse ou Monastir, avec un potentiel de "
            "valorisation moyen terme."
        ),
        "facteurs": ["Tourisme émergent", "Prix attractifs vs Sousse/Monastir", "Valorisation côtière progressive"],
    },

    # ── Sfax ──────────────────────────────────────────────────────────────────
    "Sfax": {
        "taux_vente_mensuel": 0.0055,
        "taux_location_mensuel": 0.0042,
        "prix_moyen_m2": {
            "appartement": 2800, "villa": 4600, "maison": 2400,
            "terrain": 1150, "bureau": 2800,
        },
        "loyers_moyens": {"S+1": 700, "S+2": 1050, "S+3": 1400, "S+4": 1850},
        "tension": "haute",
        "risque": "faible",
        "volatilite": 0.030,
        "description": (
            "Capitale économique du sud et deuxième ville de Tunisie, Sfax est "
            "réputée pour son tissu entrepreneurial dense et son marché "
            "immobilier solide et peu spéculatif. La demande est portée par "
            "des acheteurs locaux, une forte communauté d'affaires et une "
            "activité commerciale et industrielle soutenue."
        ),
        "facteurs": ["Capital entrepreneurial fort", "Marché solide peu spéculatif", "Forte demande commerciale", "Tissu industriel dense"],
    },

    # ── Centre-Ouest ──────────────────────────────────────────────────────────
    "Kairouan": {
        "taux_vente_mensuel": 0.0032,
        "taux_location_mensuel": 0.0025,
        "prix_moyen_m2": {
            "appartement": 1700, "villa": 2700, "maison": 1500,
            "terrain": 580, "bureau": 1400,
        },
        "loyers_moyens": {"S+1": 420, "S+2": 610, "S+3": 820, "S+4": 1080},
        "tension": "faible",
        "risque": "modéré",
        "volatilite": 0.050,
        "description": (
            "Quatrième ville sainte de l'Islam, Kairouan bénéficie d'un tourisme "
            "religieux et culturel. Le marché immobilier reste modeste mais "
            "progresse grâce à l'artisanat reconnu (tapis, poterie), aux "
            "investissements dans le secteur hôtelier et à la demande des "
            "fonctionnaires et enseignants."
        ),
        "facteurs": ["Tourisme religieux et culturel", "Artisanat à forte notoriété", "Croissance modérée stable"],
    },
    "Kasserine": {
        "taux_vente_mensuel": 0.0020,
        "taux_location_mensuel": 0.0015,
        "prix_moyen_m2": {
            "appartement": 1200, "villa": 1900, "maison": 1050,
            "terrain": 380, "bureau": 950,
        },
        "loyers_moyens": {"S+1": 290, "S+2": 420, "S+3": 560, "S+4": 730},
        "tension": "très faible",
        "risque": "élevé",
        "volatilite": 0.090,
        "description": (
            "Gouvernorat frontalier parmi les plus défavorisés du pays, Kasserine "
            "est caractérisé par un chômage élevé et un marché immobilier très "
            "déprimé. Les faibles revenus locaux limitent structurellement la "
            "demande et les perspectives de valorisation à court et moyen terme."
        ),
        "facteurs": ["Chômage parmi les plus élevés du pays", "Faibles revenus structurels", "Marché très déprimé"],
    },
    "Sidi Bouzid": {
        "taux_vente_mensuel": 0.0018,
        "taux_location_mensuel": 0.0014,
        "prix_moyen_m2": {
            "appartement": 1100, "villa": 1750, "maison": 980,
            "terrain": 350, "bureau": 880,
        },
        "loyers_moyens": {"S+1": 270, "S+2": 390, "S+3": 520, "S+4": 680},
        "tension": "très faible",
        "risque": "élevé",
        "volatilite": 0.090,
        "description": (
            "Berceau de la Révolution de 2011, Sidi Bouzid reste l'un des "
            "gouvernorats les plus pauvres de Tunisie. Le marché immobilier est "
            "quasi-informel et les prix figurent parmi les plus bas du pays. "
            "L'agriculture reste le secteur dominant avec très peu "
            "d'investissement immobilier formel enregistré."
        ),
        "facteurs": ["Économie agricole quasi-informelle", "Revenu moyen très bas", "Transactions formelles rares"],
    },

    # ── Sud-Est ───────────────────────────────────────────────────────────────
    "Gabès": {
        "taux_vente_mensuel": 0.0035,
        "taux_location_mensuel": 0.0028,
        "prix_moyen_m2": {
            "appartement": 1850, "villa": 3000, "maison": 1600,
            "terrain": 680, "bureau": 1550,
        },
        "loyers_moyens": {"S+1": 460, "S+2": 670, "S+3": 900, "S+4": 1180},
        "tension": "faible",
        "risque": "modéré",
        "volatilite": 0.058,
        "description": (
            "Gouvernorat industriel du sud-est, Gabès abrite un complexe "
            "chimique industriel majeur (phosphates, engrais). Le marché "
            "immobilier est soutenu par la demande des employés industriels "
            "mais pâtit de préoccupations environnementales persistantes. "
            "L'oasis côtière et le port confèrent un certain attrait stratégique."
        ),
        "facteurs": ["Industrie chimique et phosphatière", "Contraintes environnementales", "Oasis côtière et port actif"],
    },
    "Medenine": {
        "taux_vente_mensuel": 0.0040,
        "taux_location_mensuel": 0.0032,
        "prix_moyen_m2": {
            "appartement": 2000, "villa": 3200, "maison": 1750,
            "terrain": 800, "bureau": 1700,
        },
        "loyers_moyens": {"S+1": 500, "S+2": 730, "S+3": 980, "S+4": 1280},
        "tension": "modérée",
        "risque": "modéré",
        "volatilite": 0.052,
        "description": (
            "Gouvernorat frontalier avec la Libye, Medenine bénéficie d'un "
            "commerce transfrontalier actif. L'île de Djerba (Houmt Souk, Midoun) "
            "constitue un marché immobilier premium très prisé par la diaspora "
            "et les investisseurs européens. Ben Guerdane est un pôle "
            "commercial dynamique."
        ),
        "facteurs": ["Commerce transfrontalier libyen", "Djerba — marché premium international", "Diaspora et investisseurs européens"],
    },
    "Tataouine": {
        "taux_vente_mensuel": 0.0022,
        "taux_location_mensuel": 0.0018,
        "prix_moyen_m2": {
            "appartement": 1300, "villa": 2100, "maison": 1150,
            "terrain": 450, "bureau": 1050,
        },
        "loyers_moyens": {"S+1": 320, "S+2": 460, "S+3": 620, "S+4": 810},
        "tension": "très faible",
        "risque": "élevé",
        "volatilite": 0.078,
        "description": (
            "Gouvernorat désertique du Sud, Tataouine est connu pour ses ksour "
            "berbères et ses sites de tournage (Star Wars). Le marché immobilier "
            "formel est quasi-inexistant en dehors du chef-lieu. Le potentiel "
            "écotouristique reste très sous-exploité malgré un patrimoine exceptionnel."
        ),
        "facteurs": ["Tourisme saharien de niche", "Patrimoine berbère unique", "Très faible demande formelle"],
    },

    # ── Sud-Ouest ─────────────────────────────────────────────────────────────
    "Gafsa": {
        "taux_vente_mensuel": 0.0025,
        "taux_location_mensuel": 0.0020,
        "prix_moyen_m2": {
            "appartement": 1500, "villa": 2400, "maison": 1300,
            "terrain": 520, "bureau": 1200,
        },
        "loyers_moyens": {"S+1": 370, "S+2": 540, "S+3": 720, "S+4": 940},
        "tension": "faible",
        "risque": "élevé",
        "volatilite": 0.082,
        "description": (
            "Capital du bassin minier tunisien, Gafsa est fortement dépendante "
            "des phosphates exploités par la CPG. Les fluctuations de la "
            "production minière et les tensions sociales impactent directement "
            "le marché immobilier local, créant une volatilité supérieure "
            "à la moyenne nationale."
        ),
        "facteurs": ["Dépendance aux phosphates (CPG)", "Instabilité économique cyclique", "Tensions sociales récurrentes"],
    },
    "Tozeur": {
        "taux_vente_mensuel": 0.0030,
        "taux_location_mensuel": 0.0025,
        "prix_moyen_m2": {
            "appartement": 1600, "villa": 2600, "maison": 1400,
            "terrain": 600, "bureau": 1300,
        },
        "loyers_moyens": {"S+1": 400, "S+2": 580, "S+3": 780, "S+4": 1020},
        "tension": "faible",
        "risque": "modéré",
        "volatilite": 0.060,
        "description": (
            "Porte du désert et capitale des oasis du Jerid, Tozeur développe "
            "un tourisme saharien haut de gamme. L'aéroport international de "
            "Nefta et les hôtels de luxe (Anantara, Dar Cherait) attirent "
            "les investisseurs. Le marché immobilier touristique est en "
            "progression soutenue."
        ),
        "facteurs": ["Tourisme saharien premium en croissance", "Aéroport international", "Hôtellerie de luxe internationale"],
    },
    "Kébili": {
        "taux_vente_mensuel": 0.0020,
        "taux_location_mensuel": 0.0016,
        "prix_moyen_m2": {
            "appartement": 1150, "villa": 1850, "maison": 1000,
            "terrain": 380, "bureau": 900,
        },
        "loyers_moyens": {"S+1": 280, "S+2": 400, "S+3": 540, "S+4": 700},
        "tension": "très faible",
        "risque": "élevé",
        "volatilite": 0.090,
        "description": (
            "Gouvernorat des chott et des oasis, Kébili est parmi les moins "
            "urbanisés de Tunisie. Douz, surnommée 'porte du Sahara', attire "
            "un tourisme saharien de niche. Le marché immobilier formel est "
            "très limité, avec des transactions essentiellement informelles."
        ),
        "facteurs": ["Très faible urbanisation", "Tourisme saharien de niche (Douz)", "Marché quasi-inexistant"],
    },
}

# Listes de référence
COMPOSITIONS = ["S+1", "S+2", "S+3", "S+4"]
TYPES_BIEN = ["appartement", "villa", "maison", "terrain", "bureau"]
NOMS_GOUVERNORATS = sorted(GOUVERNORATS.keys())
