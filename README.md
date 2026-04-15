# ImmoForecast TN

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-5.4-3178C6?logo=typescript)
![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-3.4-38BDF8?logo=tailwindcss)
![License](https://img.shields.io/badge/Licence-MIT-green)

> Agent IA de prévision immobilière couvrant les **24 gouvernorats tunisiens** — prédictions distinctes sur 4 horizons temporels, positionnement marché, analyse contextuelle et recommandation différenciée selon le mode **Vente** ou **Location**.

---

## Table des matières

1. [Présentation du projet](#1-présentation-du-projet)
2. [Fonctionnalités principales](#2-fonctionnalités-principales)
3. [Architecture technique](#3-architecture-technique)
4. [Benchmarking des modèles de forecasting](#4-benchmarking-des-modèles-de-forecasting)
5. [Structure des données](#5-structure-des-données)
6. [Logique de calcul](#6-logique-de-calcul)
7. [Installation et lancement](#7-installation-et-lancement)
8. [Instructions pour Claude Code](#8-instructions-pour-claude-code)

---

## 1. Présentation du projet

**ImmoForecast TN** est une application web de prévision immobilière intelligente développée dans le cadre du Projet Intégré **NeuroNova** — Esprit 4DS10 2025-2026.

Il ne s'agit pas d'un simple calculateur de prix. C'est un **agent IA de marché** qui :

- Analyse le profil économique de chacun des 24 gouvernorats tunisiens
- Distingue fondamentalement deux marchés : la **vente** (raisonnement en prix au m²) et la **location** (raisonnement en loyer mensuel selon la composition du logement)
- Positionne le bien saisi par rapport aux prix moyens réels du marché local
- Génère un **raisonnement explicite** décrivant les dynamiques du gouvernorat sélectionné
- Produit **4 prédictions de prix strictement distinctes** sur 6, 12, 18 et 24 mois
- Évalue le niveau de risque d'investissement et formule une recommandation contextuelle

Le projet couvre l'intégralité du territoire tunisien, du Grand Tunis aux gouvernorats sahariens, avec des paramètres de marché calibrés pour chaque zone géographique.

---

## 2. Fonctionnalités principales

### Couverture géographique
| Zone | Gouvernorats |
|---|---|
| Grand Tunis | Tunis, Ariana, Ben Arous, Manouba |
| Cap Bon & Nord | Nabeul, Zaghouan, Bizerte |
| Nord-Ouest | Béja, Jendouba, Kef, Siliana |
| Sahel | Sousse, Monastir, Mahdia |
| Centre | Sfax, Kairouan, Kasserine, Sidi Bouzid |
| Sud-Est | Gabès, Medenine, Tataouine |
| Sud-Ouest | Gafsa, Tozeur, Kébili |

### Fonctionnalités détaillées

- **Sélecteur des 24 gouvernorats** — liste exhaustive des gouvernorats officiels, chargée dynamiquement depuis l'API
- **Mode Vente** — saisie du gouvernorat, type de bien (appartement / villa / maison / terrain / bureau), superficie en m² et prix au m²
- **Mode Location** — saisie du gouvernorat, composition du logement (S+1 / S+2 / S+3 / S+4) et loyer mensuel actuel
- **Saisie libre du prix** — aucun arrondi automatique (`step="any"`), la valeur saisie par l'utilisateur est transmise telle quelle
- **4 horizons de prédiction distincts** — prédictions compoundées indépendantes à +6, +12, +18 et +24 mois, toujours strictement croissantes
- **Positionnement marché** — comparaison du prix saisi avec le prix moyen du marché local, classification (sous-évalué / dans la moyenne / surévalué) et barre de positionnement visuelle
- **Analyse de marché** — paragraphe contextuel décrivant la dynamique économique du gouvernorat sélectionné et ses facteurs clés
- **Indicateur de risque** — classification Faible / Modéré / Élevé basée sur la volatilité historique du marché local
- **Recommandation de l'agent** — texte généré dynamiquement en fonction du gouvernorat, du mode, du statut prix et de la tendance
- **Graphique d'évolution** — courbe de prévision sur 24 mois avec intervalle de confiance à 90%
- **Taux de croissance annuel** — affiché en pourcentage pour chaque gouvernorat et chaque mode

---

## 3. Architecture technique

### Stack

| Couche | Technologie |
|---|---|
| API Backend | FastAPI 0.111 + Uvicorn |
| Validation | Pydantic v2 |
| Calcul | Python 3.12 + Pandas + NumPy |
| Frontend | React 18 + TypeScript 5.4 |
| Styling | Tailwind CSS 3.4 |
| Graphiques | Recharts 2.12 |
| HTTP Client | Axios 1.6 |
| Build Frontend | Vite 5.2 |

### Structure des fichiers

```
04_deployment/
├── backend/
│   ├── market_data.py      # Profils de marché — 24 gouvernorats
│   ├── agent.py            # Logique agent : vente & location séparées
│   ├── main.py             # FastAPI — routes /api/analyze/*
│   ├── schemas.py          # Modèles Pydantic (requêtes & réponses)
│   ├── predictor.py        # Ancien pipeline ML (Prophet/ARIMA/LSTM)
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.tsx                        # Orchestration des deux modes
    │   ├── components/
    │   │   ├── ForecastForm.tsx           # Formulaire dual-mode
    │   │   ├── AgentReport.tsx            # Rapport complet 5 sections
    │   │   └── ForecastChart.tsx          # Graphique d'évolution
    │   └── services/
    │       └── api.service.ts             # Types & appels HTTP
    ├── vite.config.ts
    └── package.json
```

### Séparation des responsabilités

```
market_data.py
    └── Données statiques calibrées par gouvernorat

agent.py
    ├── analyze_vente()   → positionnement, 4 horizons, reco propriétaire
    └── analyze_location() → positionnement loyer, 4 horizons, reco locataire/propriétaire

main.py
    ├── POST /api/analyze/vente
    ├── POST /api/analyze/location
    ├── GET  /api/zones
    └── GET  /api/health

Frontend
    ├── ForecastForm   → collecte les paramètres (mode, gouvernorat, prix)
    ├── AgentReport    → affiche les 5 sections du rapport
    └── ForecastChart  → courbe 24 mois + IC 90%
```

---

## 4. Benchmarking des modèles de forecasting

Plusieurs approches ont été évaluées pour la prédiction de prix immobiliers en Tunisie. Le tableau ci-dessous synthétise les résultats et les raisons du choix final.

| Modèle | Type | Avantages | Inconvénients | Adapté au cas ? |
|---|---|---|---|---|
| **Régression linéaire** | Statistique | Simple, interprétable, rapide | Suppose une tendance strictement linéaire, pas de saisonnalité | Non — trop simpliste |
| **ARIMA** | Série temporelle | Capture autocorrélations, bon sur données stationnaires | Nécessite > 2 ans de données mensuelles, pas de saisonnalité multivariée | Partiel — données insuffisantes |
| **Prophet (Meta)** | Série temporelle | Gestion saisonnalité, jours fériés, changepoints automatiques | Nécessite au moins 2 cycles saisonniers complets, fragile sur données clairsemées | Partiel — 1 seule série disponible |
| **XGBoost** | Ensemble/ML | Très performant sur données tabulaires, feature importance | Nécessite de nombreuses features exogènes (PIB, taux, démographie) indisponibles | Non — données insuffisantes |
| **LSTM** | Deep Learning | Capture patterns non-linéaires complexes, mémoire longue | Nécessite > 500 points d'entraînement, sur-apprentissage sur petits jeux | Non — données insuffisantes |
| **Compound Growth (retenu)** | Actuariel | Transparent, calibrable par zone, garantit 4 valeurs distinctes, zéro dépendance données historiques | Pas de capture des cycles économiques exogènes | **Oui — optimal pour ce cas** |

### Pourquoi le modèle Compound Growth a été retenu

Le marché immobilier tunisien présente plusieurs contraintes qui rendent les modèles ML classiques inadaptés :

1. **Données fragmentées** — les séries temporelles disponibles couvrent moins de 24 mois pour la majorité des gouvernorats, insuffisant pour entraîner ARIMA ou Prophet de manière fiable
2. **Hétérogénéité géographique extrême** — le marché de Tunis (3 500 TND/m²) est structurellement différent de celui de Sidi Bouzid (1 100 TND/m²) ; un modèle unique ne peut capturer cette diversité
3. **Intelligibilité requise** — l'agent doit pouvoir expliquer sa prédiction à l'utilisateur ; une boîte noire LSTM ne produit pas de raisonnement lisible
4. **Distinction vente/location** — les deux marchés ont des dynamiques différentes et des taux de croissance distincts, ce que le compound growth gère nativement

Le modèle **ARIMA + Prophet + LSTM** reste disponible via l'endpoint `/api/predict` (ancien pipeline) pour les gouvernorats disposant de séries temporelles suffisantes.

---

## 5. Structure des données

### Profil de marché par gouvernorat (`market_data.py`)

```python
{
    "Tunis": {
        "taux_vente_mensuel": 0.0065,          # Taux de croissance mensuel en vente
        "taux_location_mensuel": 0.0048,        # Taux de croissance mensuel en location
        "prix_moyen_m2": {
            "appartement": 3500,                # Prix moyen au m² (TND)
            "villa":        5800,
            "maison":       2900,
            "terrain":      1500,
            "bureau":       3200,
        },
        "loyers_moyens": {
            "S+1": 900,                         # Loyer mensuel moyen (TND)
            "S+2": 1350,
            "S+3": 1800,
            "S+4": 2500,
        },
        "tension":    "très haute",             # Tension immobilière locale
        "risque":     "faible",                 # Risque d'investissement
        "volatilite": 0.038,                    # Volatilité du marché (std annualisée)
        "description": "...",                   # Analyse contextuelle générée
        "facteurs":   ["...", "..."],            # Facteurs clés du marché
    },
    ...                                         # × 24 gouvernorats
}
```

### Requête utilisateur

**Mode Vente**
```json
{
  "gouvernorat":  "Sousse",
  "type_bien":    "appartement",
  "superficie":   85,
  "prix_m2_saisi": 2800
}
```

**Mode Location**
```json
{
  "gouvernorat": "Monastir",
  "composition": "S+2",
  "loyer_saisi": 1300
}
```

### Réponse agent (`AgentResponse`)

```json
{
  "mode":                    "vente",
  "gouvernorat":             "Sousse",
  "type_bien":               "appartement",
  "superficie":              85,
  "valeur_saisie":           2800,
  "valeur_totale_actuelle":  238000,
  "prix_moyen_marche":       3000,
  "diff_vs_marche_pct":      -6.7,
  "statut_prix":             "sous-évalué",
  "taux_mensuel":            0.006,
  "taux_annuel":             7.44,
  "horizons": {
    "6":  { "valeur": 2902.32, "variation_pct": 3.65 },
    "12": { "valeur": 3008.39, "variation_pct": 7.44 },
    "18": { "valeur": 3118.33, "variation_pct": 11.37 },
    "24": { "valeur": 3232.28, "variation_pct": 15.44 }
  },
  "tendance":         "hausse",
  "risque":           "Faible",
  "tension":          "haute",
  "analyse_marche":   "Troisième ville de Tunisie et capitale du Sahel...",
  "facteurs":         ["Hub touristique", "Ville universitaire", "Diaspora active"],
  "recommandation":   "Bonne entrée de marché : le prix est -6.7% sous la moyenne...",
  "points": [
    { "date": "2026-05-01", "prix_predit": 2816.8, "ic_bas": 2752.1, "ic_haut": 2881.5 },
    "... (24 points mensuels)"
  ]
}
```

---

## 6. Logique de calcul

### Formule de compound growth

```
prix_N = prix_saisi × (1 + taux_mensuel)^N
```

où `N` ∈ {6, 12, 18, 24} mois.

Les 4 valeurs sont toujours **strictement croissantes** (si `taux_mensuel > 0`) et **distinctes** par construction mathématique. La valeur à N=6 est nécessairement différente de N=12, etc.

### Exemple numérique — Tunis, appartement, 3 200 TND/m²

| Horizon | Calcul | Résultat | Variation |
|---|---|---|---|
| +6 mois  | `3200 × (1.0065)^6`  | 3 326 TND/m² | +3.94% |
| +12 mois | `3200 × (1.0065)^12` | 3 458 TND/m² | +8.06% |
| +18 mois | `3200 × (1.0065)^18` | 3 595 TND/m² | +12.34% |
| +24 mois | `3200 × (1.0065)^24` | 3 738 TND/m² | +16.81% |

### Différence vente vs location

| Dimension | Vente | Location |
|---|---|---|
| Unité de saisie | Prix au m² (TND/m²) | Loyer mensuel (TND/mois) |
| Référence marché | `prix_moyen_m2[type_bien]` | `loyers_moyens[composition]` |
| Taux appliqué | `taux_vente_mensuel` | `taux_location_mensuel` |
| Valeur totale | `prix_m2 × superficie` | — |
| Recommandation | Acheteur / vendeur | Locataire / propriétaire |
| Classification | sous-évalué / dans la moyenne / surévalué | en-dessous / aligné / au-dessus du marché |

Les deux modes n'utilisent **jamais** les mêmes taux ni la même logique de recommandation.

### Génération du raisonnement contextuel

L'agent génère le texte de recommandation en combinant :

1. **Le statut prix** (5 niveaux : très sous-évalué → fortement surévalué)
2. **La tendance** (hausse / stable / baisse) calculée à partir de `variation_pct_24`
3. **Le gouvernorat** (nom explicite dans le texte)
4. **Le taux annuel** (affiché en %)
5. **Le niveau de risque** (avertissement ajouté si Élevé ou Modéré)

Chaque combinaison produit un texte distinct — aucun texte n'est identique pour deux gouvernorats différents ou deux niveaux de prix différents.

### Intervalle de confiance (graphique)

```
ic_width = prix × volatilite × sqrt(mois / 24)
ic_bas   = prix - ic_width
ic_haut  = prix + ic_width
```

La volatilité est propre à chaque gouvernorat (de 0.030 pour Sfax à 0.090 pour Kébili). L'IC s'élargit progressivement avec le temps.

---

## 7. Installation et lancement

### Prérequis

- Python 3.12+
- Node.js 18+ / npm 9+

### Backend

```bash
# 1. Cloner le dépôt
git clone https://github.com/nourrajhii/Esprit-PI-4DS10-2025-2026-NeuroNova.git
cd Esprit-PI-4DS10-2025-2026-NeuroNova

# 2. Créer et activer un environnement virtuel
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

# 3. Installer les dépendances
pip install fastapi uvicorn pydantic pandas numpy

# 4. Démarrer le serveur
cd 04_deployment/backend
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Le backend est disponible sur **http://localhost:8001**
Documentation interactive : **http://localhost:8001/docs**

### Frontend

```bash
cd 04_deployment/frontend

# Installer les dépendances
npm install

# Démarrer le serveur de développement
npm run dev
```

Le frontend est disponible sur **http://localhost:3000** (proxy automatique vers le backend sur 8001).

### Variables d'environnement (optionnel)

```bash
# .env dans 04_deployment/frontend/
VITE_API_BASE_URL=http://localhost:8001
```

### Endpoints API disponibles

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/api/analyze/vente` | Analyse d'un bien en vente |
| `POST` | `/api/analyze/location` | Analyse d'un bien en location |
| `GET`  | `/api/zones` | Gouvernorats, types, compositions |
| `GET`  | `/api/health` | Statut de l'API |

### Exemple d'appel direct

```bash
curl -X POST http://localhost:8001/api/analyze/vente \
  -H "Content-Type: application/json" \
  -d '{
    "gouvernorat": "Sfax",
    "type_bien": "appartement",
    "superficie": 100,
    "prix_m2_saisi": 2600
  }'
```

---

## 8. Instructions pour Claude Code

Ce projet est un agent IA de prévision immobilière pour la Tunisie. Il couvre les 24 gouvernorats avec des profils de marché distincts. Le mode Vente travaille en prix au m² et le mode Location en loyer mensuel selon la composition du logement (S+1, S+2, S+3, S+4). Les prédictions sont calculées par compound growth sur 4 horizons (6, 12, 18, 24 mois) avec des taux différents par gouvernorat et par mode. L'agent génère une analyse de marché, un positionnement du bien, un indicateur de risque et une recommandation contextuelle. Toute modification doit préserver cette logique différenciée entre vente et location, garantir que les 4 valeurs prédites sont strictement différentes, et que le champ prix accepte n'importe quelle valeur entière saisie sans correction automatique.

---

*Projet NeuroNova · Esprit PI 4DS10 2025-2026 · Marché immobilier tunisien*
