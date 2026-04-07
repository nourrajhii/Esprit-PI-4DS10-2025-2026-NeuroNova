# PI_DS_EstateMind

EstateMind – Tunisian Real Estate Intelligence Platform

## Overview

This project was developed as part of the PI – Data Science Program at Esprit School of Engineering (Academic Year 2025–2026).
EstateMind is an AI-powered platform for the Tunisian real estate market, combining automated data collection, price prediction, legal assistance, and 3D property visualization into a unified intelligent system.

## Features 

  ***AI Scraping Agent***  — Automated collection, deduplication, and enrichment of real estate listings from multiple Tunisian platforms

  
  ***Price & Investment Analytics***  — ML-based price prediction, zone segmentation, and anomaly detection

  
 ***Legal Assistance Chatbot***  — RAG-based agent answering questions on Tunisian real estate law 

 
***3D Property Visualization***  — AI-generated 3D property models with interactive city map and district simulation


***Dashboards & Reporting*** — KPIs, market analysis, investment recommendations, and monitoring alerts

## Tech Stack

 ## Frontend: 

   *Main web interface* : Angular 

   
   *Legal chatbot & analytics*: Streamlit

   
   *3D property visualization* :  UIThree.js / Babylon.js

   
   *Interactive city maps & districts* : Mapbox GL JS / Leaflet.js

   
   *BI dashboards & KPI reporting* : PowerBI

   

##  Backend : 
   *Primary language* : Python 3.11 

   
   *REST API backend*: FastAPI

   
   *Web scraping agent* : beautiful Soup , GoogleSearch

   
   *models* : scikit-learn / XGBoost..

   
   *RAG framework for legal chatbot* : LangChain

   
   *Local LLM inference*: Ollama (llama3.2:3b)

   
   *Structured property data* : PostgreSQL

   
   *Unstructured listings & legal texts* : MongoDB

   
   *Containerization & deployment* :Docker

   
   *Monitoring & alerting*: Kibana & ElasticSearch

   

## Architecture 

EstateMind

├── BO1  AI Scraping       → BeautifulSoup · GoogleSearch

├── BO2  Analytics         → XGBoost

├── BO3  Legal Chatbot     → LangChain · llama3.2

├── BO4  3D Visualization  → Three.js · Mapbox

├── Presentation           → Angular · Streamlit · Power BI

└── Infrastructure         → FastAPI · Docker

## Contributors

**Nour Rajhi** 
**Oumaima Nacef** 
**Yosri Awedi** 
**Baha Saadaoui**
**Dhia Romdhane**
**Taha Yassine Bouguerra**


## Academic Context

Developed at Esprit School of Engineering – Tunisia  
PIDS – 4DS | 2025–2026


## Getting Started

python --version

**Running AI Scraping Agent**  :
python mubawab_scraper.py
python main.py

**Running the Legal Chatbot** :
Ollama — download from https://ollama.com
ollama pull llama3.2:3b

ollama pull nomic-embed-text

cd legal_agent

python build_db.py

python -m streamlit run app.py

## Acknowledgments


- **Esprit School of Engineering – Tunisia** — academic supervision and institutional support  
- **Tunisian Ministry of Finance** — Loi de Finances 2025 (n°48-2024)  
- **Code des Droits Réels** — Loi n°65-5 du 12 février 1965  
- **Loi sur la Promotion Immobilière** — Loi n°90-17 du 26 février 1990  
- **مجلة الحقوق العينية (Journals of Real Rights)** — for reference on Tunisian real estate law  
- **Meta AI** — llama3.2 open-source language model  
- **Nomic AI** — nomic-embed-text embedding model   
- **LangChain** — RAG framework for legal chatbot  
- **Streamlit** — ML application UI framework for chatbot and analytics  
- **Three.js / Babylon.js** — for 3D property visualization  
- **Mapbox GL JS / Leaflet.js** — for interactive city maps and district simulation  
- **PowerBI** — for BI dashboards and KPI reporting  
- **Docker** — containerization and deployment  
- **Kibana & ElasticSearch** — monitoring and alerting

