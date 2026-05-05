# ⚖️ Legal Agent API — Backend FastAPI v2

Assistant juridique immobilier tunisien : COC, Droits Réels, Urbanisme, Fiscalité 2025.

---

## 📁 Structure du projet

```
legal_agent_api/
├── app/
│   ├── main.py                        # FastAPI — point d'entrée
│   ├── api/routes/
│   │   ├── chat.py                    # POST /chat
│   │   ├── sessions.py                # GET/DELETE /sessions
│   │   └── admin.py                   # /admin/reload-db, /admin/clear-cache
│   ├── core/
│   │   ├── config.py                  # Paramètres globaux
│   │   ├── language.py                # detect_language() + detect_question_type()
│   │   └── prompts.py                 # build_prompt() FR / AR
│   ├── services/
│   │   ├── rag.py                     #  Orchestrateur principal
│   │   ├── hardcoded.py               # Règles juridiques hardcodées
│   │   ├── calculator.py              # TVA, droits, mensualité, rendement
│   │   ├── vector_store.py            # Singleton FAISS + scoring
│   │   ├── llm.py                     # OllamaLLM + clean_response()
│   │   ├── cache.py                   # Cache JSON (similarité Jaccard)
│   │   └── memory.py                  # Sessions conversationnelles JSON
│   └── models/
│       ├── request.py                 # ChatRequest (Pydantic)
│       └── response.py                # ChatResponse, MetricItem, etc.
├── data/                              # Fichiers TXT/PDF à indexer
├── tests/
│   └── Legal_Agent_API.postman_collection.json
├── build_db.py
└── requirements.txt
```

---

## 🚀 Installation

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Lancer Ollama
ollama pull nomic-embed-text && ollama pull llama3.2:3b && ollama serve

# 3. Placer les fichiers dans data/ puis construire FAISS
python build_db.py

# 4. Démarrer l'API
uvicorn app.main:app --reload --port 8000
```

Swagger UI : http://localhost:8000/docs

---

## 📡 Endpoints

| Méthode | URL | Description |
|---------|-----|-------------|
| GET  | /health | Statut API |
| POST | /chat | Question juridique |
| GET  | /sessions | Liste sessions |
| GET  | /sessions/{id} | Détail session |
| DELETE | /sessions/{id} | Supprimer session |
| POST | /admin/reload-db | Recharger FAISS |
| POST | /admin/clear-cache | Vider cache |
| GET  | /admin/cache-stats | Stats cache |

---

## 🔄 Flux de traitement

```
Question → chitchat? → réponse immédiate (0 LLM)
         → calcul?   → résultat direct   (0 LLM)
         → cache?    → réponse cachée    (0 LLM)
         → hardcoded + FAISS → LLM → réponse
```

---

## 🧪 Postman

Import : `tests/Legal_Agent_API.postman_collection.json`
Variable `base_url` = `http://localhost:8000`
