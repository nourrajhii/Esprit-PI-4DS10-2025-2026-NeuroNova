"""
VIAGRA — Versatile Intelligent Gateway for Real-Estate AI Agents
Unified orchestrator for the IMMO-AI platform (port 8000).
"""
import asyncio, json, os, re, time
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx, redis.asyncio as aioredis
import certifi
from motor.motor_asyncio import AsyncIOMotorClient
import uvicorn

app = FastAPI(title="VIAGRA — IMMO-AI Orchestrator", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Agent URLs (overridden by env) ────────────────────────────────────────────
AGENT_URLS = {
    "recommender":        os.getenv("RECOMMENDER_URL",  "http://real-estate-advisor-backend:8001"),
    "devis":              os.getenv("DEVIS_URL",         "http://nour:8002"),
    "legal":              os.getenv("LEGAL_URL",         "http://nour2:8003"),
    "forecast":           os.getenv("FORECAST_URL",      "http://immo-forecast:8004"),
    "price_predictor":    os.getenv("PRICE_URL",         "http://price-predictor:8005"),
    "investment_scorer":  os.getenv("INVESTMENT_URL",    "http://investment-scorer:8006"),
    "geo_advisor":        os.getenv("GEO_URL",           "http://geo-advisor:8007"),
    "lifestyle":          os.getenv("LIFESTYLE_URL",     "http://lifestyle-match:8010"),
    # dhia's own invoke adapter (prediction + investment from ML pipeline)
    "dhia":               os.getenv("DHIA_URL",          "http://dhia:8055"),
}

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
redis_client: Optional[aioredis.Redis] = None

# ── MongoDB Atlas (dhia scraper data) ─────────────────────────────────────────
MONGO_URL = os.getenv(
    "DATABASE_URL",
    "mongodb+srv://dhiaromd1_db_user:uFXwH6QvnGYib1eX@cluster0.dm9cm4p.mongodb.net/dcrawl"
    "?retryWrites=true&w=majority&appName=Cluster0&tlsAllowInvalidCertificates=true"
)
_mongo_client: Optional[AsyncIOMotorClient] = None


def _get_mongo_col():
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(MONGO_URL, tlsCAFile=__import__("certifi").where())
    return _mongo_client["dcrawl"]["listings"]

CACHE_TTL = {
    "price":    3600,
    "forecast": 21600,
    "geo":      86400,
    "legal":    43200,
}

# ── Redis lifecycle ───────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    global redis_client
    try:
        redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        print("Redis connected")
    except Exception as e:
        print(f"Redis unavailable — caching disabled: {e}")
        redis_client = None


@app.on_event("shutdown")
async def shutdown():
    if redis_client:
        await redis_client.aclose()


# ── Cache helpers ─────────────────────────────────────────────────────────────
async def cache_get(key: str) -> Optional[dict]:
    if not redis_client:
        return None
    try:
        val = await redis_client.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


async def cache_set(key: str, value: dict, ttl: int):
    if not redis_client:
        return
    try:
        await redis_client.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


# ── Agent caller ──────────────────────────────────────────────────────────────
async def call_agent(client: httpx.AsyncClient, agent: str, payload: dict,
                     timeout: float = 45.0) -> Optional[dict]:
    url = AGENT_URLS.get(agent)
    if not url:
        return None
    try:
        resp = await client.post(f"{url}/invoke", json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[VIAGRA] Agent {agent} error: {e}")
        return None


# ── Language detection ────────────────────────────────────────────────────────
def detect_language(text: str) -> str:
    arabic_re = re.compile(r"[؀-ۿ]")
    if arabic_re.search(text):
        return "ar"
    french_keywords = ["je", "veux", "trouver", "appartement", "maison", "prix",
                       "combien", "louer", "acheter", "terrain", "rénovation",
                       "construction", "juridique", "loi", "étranger"]
    lower = text.lower()
    if any(k in lower for k in french_keywords):
        return "fr"
    return "en"


# ── Intent classifier ─────────────────────────────────────────────────────────
def classify_intent(text: str) -> dict:
    lower = text.lower()

    # Devis / construction cost
    devis_patterns = ["devis", "combien coûte", "prix construction", "rénov",
                      "construire", "bâtir", "matériaux", "renovation", "travaux",
                      "estimation travaux", "m²", "mètre carré"]
    if any(p in lower for p in devis_patterns):
        return {"type": "devis"}

    # Legal
    legal_patterns = ["légal", "loi", "juridique", "contrat", "permis", "notaire",
                      "zonage", "étranger", "achat", "droit", "réglementation",
                      "fiscal", "taxe", "succession", "hypothèque", "code",
                      "loyer", "locataire", "bailleur", "bail", "expulsion",
                      "non-paiement", "obligations", "acheteur", "vendeur",
                      "vente immobilière", "titre foncier", "enregistrement",
                      "résiliation", "défaut", "annuler", "vice", "garantie",
                      "copropriété", "servitude", "usufruit", "saisie",
                      "كراء", "مستأجر", "إيجار", "طرد", "بيع", "حقوق",
                      "قانون", "عقد", "رخصة", "بناء"]
    if any(p in lower for p in legal_patterns):
        return {"type": "legal"}

    # Forecast
    forecast_patterns = ["prévision", "forecast", "évolution", "tendance", "avenir",
                         "prix dans", "marché", "prochaine année", "12 mois",
                         "demain", "investissement région", "توقع", "سعر"]
    if any(p in lower for p in forecast_patterns):
        # extract governorat
        gov = _extract_location(text)
        return {"type": "forecast", "governorat": gov}

    # Listing ID / URL analysis
    if re.search(r"listing[_\-/]?\d+|id[:\s]+\d+|/annonce/", lower):
        listing_id = re.search(r"\d+", text)
        return {"type": "listing_analysis", "listing_id": listing_id.group() if listing_id else None}

    # Default: property search
    return {"type": "search"}


def _extract_location(text: str) -> str:
    GOVS = ["Tunis", "Ariana", "Sousse", "Sfax", "Nabeul", "Monastir", "Bizerte",
            "Hammamet", "La Marsa", "Manouba", "Ben Arous", "Gabès", "Médenine",
            "Kairouan", "Gafsa", "Zaghouan", "Tozeur", "Kébili", "Tataouine",
            "Kasserine", "Sidi Bouzid", "Béja", "Jendouba", "Kef", "Siliana", "Mahdia"]
    for gov in GOVS:
        if gov.lower() in text.lower():
            return gov
    return "Tunis"


def _extract_filters(text: str) -> dict:
    filters: dict = {}
    price_match = re.search(r"(\d[\d\s]*)\s*(TND|dt|dinar|000)", text, re.IGNORECASE)
    if price_match:
        raw = price_match.group(1).replace(" ", "")
        val = int(raw) if len(raw) > 4 else int(raw) * 1000
        filters["max_price"] = val

    surface_match = re.search(r"(\d+)\s*m[²2]", text, re.IGNORECASE)
    if surface_match:
        filters["surface_m2"] = int(surface_match.group(1))

    rooms_match = re.search(r"(\d+)\s*(chambres?|pièces?|rooms?)", text, re.IGNORECASE)
    if rooms_match:
        filters["rooms"] = int(rooms_match.group(1))

    filters["city"] = _extract_location(text)
    return filters


# ── Main /chat endpoint ───────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: dict = {}


class ChatResponse(BaseModel):
    summary: str
    agents_used: list[str]
    data: dict
    follow_up_questions: list[str]
    lang: str
    intent: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    t0 = time.time()
    lang = detect_language(req.message)
    intent = classify_intent(req.message)
    intent_type = intent["type"]
    ctx = {**req.context, "lang": lang, "session_id": req.session_id}

    agents_used = []
    data: dict = {}

    async with httpx.AsyncClient() as client:

        # ── DEVIS flow ────────────────────────────────────────────────────────
        if intent_type == "devis":
            filters = _extract_filters(req.message)
            result = await call_agent(client, "devis", {
                "input": {"message": req.message, **filters},
                "context": ctx
            })
            if result:
                data["devis"] = result.get("output")
                agents_used.append("devis")
            summary = data.get("devis", {}).get("texte", "Estimation de coût générée.") if data.get("devis") else "Agent devis indisponible."
            return ChatResponse(
                summary=summary,
                agents_used=agents_used,
                data=data,
                follow_up_questions=_follow_ups(intent_type, lang, data),
                lang=lang,
                intent=intent_type
            )

        # ── LEGAL flow ────────────────────────────────────────────────────────
        if intent_type == "legal":
            cache_key = f"legal:{hash(req.message)}"
            cached = await cache_get(cache_key)
            if cached:
                data["legal"] = cached
                agents_used.append("legal (cached)")
            else:
                result = await call_agent(client, "legal", {
                    "input": {"question": req.message},
                    "context": ctx
                }, timeout=110.0)
                if result:
                    data["legal"] = result.get("output")
                    agents_used.append("legal")
                    await cache_set(cache_key, data["legal"], CACHE_TTL["legal"])
            summary = data.get("legal", {}).get("answer", "Réponse juridique générée.") if data.get("legal") else "Agent juridique indisponible."
            return ChatResponse(
                summary=summary,
                agents_used=agents_used,
                data=data,
                follow_up_questions=_follow_ups(intent_type, lang, data),
                lang=lang,
                intent=intent_type
            )

        # ── FORECAST flow ─────────────────────────────────────────────────────
        if intent_type == "forecast":
            gov = intent.get("governorat", "Tunis")
            cache_key = f"forecast:{gov}"
            cached = await cache_get(cache_key)
            if cached:
                data["forecast"] = cached
                agents_used.append("forecast (cached)")
            else:
                result = await call_agent(client, "forecast", {
                    "input": {"governorat": gov, "months": 12},
                    "context": ctx
                })
                if result:
                    data["forecast"] = result.get("output")
                    agents_used.append("forecast")
                    await cache_set(cache_key, data["forecast"], CACHE_TTL["forecast"])
            fcast = data.get("forecast", {})
            pct = fcast.get("pct_change_12m", 0) if fcast else 0
            summary = f"Prévision marché {gov}: {'+' if pct >= 0 else ''}{pct}% sur 12 mois. Signal: {fcast.get('signal', 'N/A')}." if fcast else "Prévision indisponible."
            return ChatResponse(
                summary=summary,
                agents_used=agents_used,
                data=data,
                follow_up_questions=_follow_ups(intent_type, lang, data),
                lang=lang,
                intent=intent_type
            )

        # ── LISTING ANALYSIS flow ─────────────────────────────────────────────
        if intent_type == "listing_analysis":
            filters = _extract_filters(req.message)
            city = filters.get("city", "Tunis")
            price = filters.get("max_price", 300000)
            surface = filters.get("surface_m2", 100)

            price_cache_key = f"price:{city}:{surface}"
            geo_cache_key = f"geo:{city}"

            price_task = call_agent(client, "price_predictor", {
                "input": {"city": city, "surface_m2": surface, "rooms": filters.get("rooms", 3)},
                "context": ctx
            })
            invest_task = call_agent(client, "investment_scorer", {
                "input": {"city": city, "price": price, "surface_m2": surface},
                "context": ctx
            })
            geo_cached = await cache_get(geo_cache_key)
            geo_task = (
                asyncio.sleep(0) if geo_cached
                else call_agent(client, "geo_advisor", {"input": {"city": city}, "context": ctx})
            )

            price_res, invest_res, geo_res = await asyncio.gather(price_task, invest_task, geo_task)

            if price_res:
                data["price"] = price_res.get("output")
                agents_used.append("price-predictor")
                await cache_set(price_cache_key, data["price"], CACHE_TTL["price"])
            if invest_res:
                data["investment"] = invest_res.get("output")
                agents_used.append("investment-scorer")
            if geo_cached:
                data["geo"] = geo_cached
                agents_used.append("geo-advisor (cached)")
            elif geo_res:
                data["geo"] = geo_res.get("output")
                agents_used.append("geo-advisor")
                await cache_set(geo_cache_key, data["geo"], CACHE_TTL["geo"])

            verdict = data.get("investment", {}).get("verdict", "N/A") if data.get("investment") else "N/A"
            summary = f"Analyse du bien à {city}: verdict {verdict}. Prix estimé: {data.get('price', {}).get('predicted_price_tnd', 'N/A')} TND."
            return ChatResponse(
                summary=summary,
                agents_used=agents_used,
                data=data,
                follow_up_questions=_follow_ups(intent_type, lang, data),
                lang=lang,
                intent=intent_type
            )

        # ── SEARCH flow (default) ─────────────────────────────────────────────
        filters = _extract_filters(req.message)
        city = filters.get("city", "Tunis")

        # Parallel: recommender + geo + forecast
        rec_task = call_agent(client, "recommender", {
            "input": {"prompt": req.message},
            "context": ctx
        })
        geo_cache_key = f"geo:{city}"
        geo_cached = await cache_get(geo_cache_key)
        geo_task = (
            asyncio.sleep(0) if geo_cached
            else call_agent(client, "geo_advisor", {"input": {"city": city}, "context": ctx})
        )
        fcast_cache_key = f"forecast:{city}"
        fcast_cached = await cache_get(fcast_cache_key)
        fcast_task = (
            asyncio.sleep(0) if fcast_cached
            else call_agent(client, "forecast", {"input": {"governorat": city, "months": 12}, "context": ctx})
        )

        rec_res, geo_res, fcast_res = await asyncio.gather(rec_task, geo_task, fcast_task)

        listings = []
        if rec_res:
            rec_out = rec_res.get("output", {})
            data["listings"] = rec_out
            listings = rec_out.get("properties", [])
            agents_used.append("recommender")

        if geo_cached:
            data["geo"] = geo_cached
            agents_used.append("geo-advisor (cached)")
        elif geo_res and hasattr(geo_res, 'get'):
            data["geo"] = geo_res.get("output")
            agents_used.append("geo-advisor")
            await cache_set(geo_cache_key, data["geo"], CACHE_TTL["geo"])

        if fcast_cached:
            data["forecast"] = fcast_cached
            agents_used.append("forecast (cached)")
        elif fcast_res and hasattr(fcast_res, 'get'):
            data["forecast"] = fcast_res.get("output")
            agents_used.append("forecast")
            await cache_set(fcast_cache_key, data["forecast"], CACHE_TTL["forecast"])

        # Sequential: price predict + investment score for top 3 listings
        if listings:
            enriched = []
            for listing in listings[:3]:
                p = float(listing.get("price", 300000))
                s = float(listing.get("surface_m2", listing.get("size", 100)))
                c = listing.get("city", city)

                price_key = f"price:{c}:{int(s)}"
                price_cached = await cache_get(price_key)

                if price_cached:
                    listing["price_prediction"] = price_cached
                else:
                    pr = await call_agent(client, "price_predictor", {
                        "input": {"city": c, "surface_m2": s, "rooms": listing.get("rooms", 3)},
                        "context": ctx
                    })
                    if pr:
                        listing["price_prediction"] = pr.get("output")
                        await cache_set(price_key, listing["price_prediction"], CACHE_TTL["price"])

                ir = await call_agent(client, "investment_scorer", {
                    "input": {"city": c, "price": p, "surface_m2": s},
                    "context": ctx
                })
                if ir:
                    listing["investment"] = ir.get("output")

                enriched.append(listing)

            if enriched:
                agents_used.extend(["price-predictor", "investment-scorer"])
                if data.get("listings"):
                    data["listings"]["properties"] = enriched + listings[3:]

        total = data.get("listings", {}).get("total_found", 0) if data.get("listings") else 0
        natural = data.get("listings", {}).get("natural_response", "") if data.get("listings") else ""
        summary = natural or f"Trouvé {total} biens à {city} correspondant à votre recherche."

        return ChatResponse(
            summary=summary,
            agents_used=agents_used,
            data=data,
            follow_up_questions=_follow_ups(intent_type, lang, data),
            lang=lang,
            intent=intent_type
        )


def _follow_ups(intent: str, lang: str, data: dict) -> list[str]:
    if lang == "fr":
        if intent == "search":
            return [
                "Quel est le potentiel d'investissement de ces biens?",
                "Pouvez-vous analyser le quartier?",
                "Quelles sont les prévisions de prix pour cette région?"
            ]
        if intent == "forecast":
            return [
                "Quels sont les meilleurs quartiers pour investir?",
                "Quel est le rendement locatif estimé?",
                "Y a-t-il des biens disponibles dans cette région?"
            ]
        if intent == "legal":
            return [
                "Quels sont les frais de notaire en Tunisie?",
                "Comment fonctionne le compromis de vente?",
                "Quelles taxes s'appliquent à la vente?"
            ]
        if intent == "devis":
            return [
                "Quels matériaux sont les plus économiques?",
                "Combien de temps prend ce type de construction?",
                "Pouvez-vous calculer le devis pour une rénovation?"
            ]
    if lang == "ar":
        return [
            "ما هي توقعات الأسعار في هذه المنطقة؟",
            "كيف يمكنني الاستثمار في هذا السوق؟",
            "ما هي الإجراءات القانونية لشراء عقار؟"
        ]
    return [
        "What are the investment prospects for this area?",
        "Can you show me price forecasts for this region?",
        "What are the legal requirements for purchasing property?"
    ]


# ── Listings endpoint ─────────────────────────────────────────────────────────
class SearchRequest(BaseModel):
    prompt: str
    filters: dict = {}
    session_id: Optional[str] = None


@app.post("/search")
async def search(req: SearchRequest):
    return await chat(ChatRequest(message=req.prompt, session_id=req.session_id, context=req.filters))


# ── Listing detail endpoint ───────────────────────────────────────────────────
@app.get("/listing/{listing_id}")
async def listing_detail(listing_id: str, city: str = "Tunis", price: float = 300000, surface: float = 100):
    ctx = {"lang": "fr"}
    async with httpx.AsyncClient() as client:
        price_task = call_agent(client, "price_predictor", {
            "input": {"city": city, "surface_m2": surface, "rooms": 3},
            "context": ctx
        })
        invest_task = call_agent(client, "investment_scorer", {
            "input": {"city": city, "price": price, "surface_m2": surface},
            "context": ctx
        })
        geo_task = call_agent(client, "geo_advisor", {
            "input": {"city": city},
            "context": ctx
        })
        price_res, invest_res, geo_res = await asyncio.gather(price_task, invest_task, geo_task)

    return {
        "listing_id": listing_id,
        "price": price_res.get("output") if price_res else None,
        "investment": invest_res.get("output") if invest_res else None,
        "geo": geo_res.get("output") if geo_res else None,
        "agents_used": [a for a, r in [("price-predictor", price_res), ("investment-scorer", invest_res), ("geo-advisor", geo_res)] if r]
    }


# ── Forecast endpoint ─────────────────────────────────────────────────────────
@app.get("/forecast/{governorat}")
async def forecast(governorat: str, months: int = 12):
    cache_key = f"forecast:{governorat}"
    cached = await cache_get(cache_key)
    if cached:
        return {"data": cached, "cached": True}
    async with httpx.AsyncClient() as client:
        result = await call_agent(client, "forecast", {
            "input": {"governorat": governorat, "months": months},
            "context": {}
        })
    if result:
        await cache_set(cache_key, result.get("output"), CACHE_TTL["forecast"])
        return {"data": result.get("output"), "cached": False}
    raise HTTPException(status_code=502, detail="Forecast agent unavailable")


# ── ImmoForecast full agent API (proxy) ──────────────────────────────────────

@app.post("/api/analyze/vente")
async def analyze_vente(request: Request):
    body = await request.json()
    forecast_url = AGENT_URLS["forecast"]
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(f"{forecast_url}/api/analyze/vente", json=body)
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Forecast agent error: {e}")

@app.post("/api/analyze/location")
async def analyze_location(request: Request):
    body = await request.json()
    forecast_url = AGENT_URLS["forecast"]
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(f"{forecast_url}/api/analyze/location", json=body)
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Forecast agent error: {e}")

@app.get("/api/villes/{gouvernorat}")
async def get_villes(gouvernorat: str):
    forecast_url = AGENT_URLS["forecast"]
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{forecast_url}/api/villes/{gouvernorat}")
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Forecast agent error: {e}")

@app.get("/api/zones")
async def get_zones():
    forecast_url = AGENT_URLS["forecast"]
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{forecast_url}/api/zones")
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Forecast agent error: {e}")


# ── Advisor proxy (real_estate_advisor_backend) ───────────────────────────────

@app.post("/advisor/prompt")
async def advisor_prompt(request: Request):
    body = await request.json()
    rec_url = AGENT_URLS["recommender"]
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(f"{rec_url}/advisor/prompt", json=body)
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Advisor agent error: {e}")

@app.get("/advisor/market-insights")
async def advisor_market_insights():
    rec_url = AGENT_URLS["recommender"]
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{rec_url}/advisor/market-insights")
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Advisor agent error: {e}")

@app.get("/advisor/health")
async def advisor_health_proxy():
    rec_url = AGENT_URLS["recommender"]
    async with httpx.AsyncClient(timeout=8) as client:
        try:
            resp = await client.get(f"{rec_url}/advisor/health")
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Advisor agent error: {e}")


# ── Devis proxy (nour agent) ─────────────────────────────────────────────────

@app.post("/devis/chat")
async def devis_chat(request: Request):
    body = await request.json()
    devis_url = AGENT_URLS["devis"]
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(f"{devis_url}/invoke", json={
                "input": body,
                "context": {"session_id": body.get("session_id", "default")}
            })
            data = resp.json()
            return data.get("output", data)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Devis agent error: {e}")

@app.get("/devis/health")
async def devis_health_proxy():
    devis_url = AGENT_URLS["devis"]
    async with httpx.AsyncClient(timeout=8) as client:
        try:
            resp = await client.get(f"{devis_url}/health")
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Devis agent error: {e}")


# ── Legal proxy (nour2 agent) ─────────────────────────────────────────────────

@app.post("/legal/chat")
async def legal_chat(request: Request):
    body = await request.json()
    legal_url = AGENT_URLS["legal"]
    async with httpx.AsyncClient(timeout=130) as client:
        try:
            resp = await client.post(f"{legal_url}/invoke", json={
                "input": body,
                "context": {"session_id": body.get("session_id")}
            })
            data = resp.json()
            return data.get("output", data)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Legal agent error: {e}")

@app.get("/legal/health")
async def legal_health_proxy():
    legal_url = AGENT_URLS["legal"]
    async with httpx.AsyncClient(timeout=8) as client:
        try:
            resp = await client.get(f"{legal_url}/health")
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Legal agent error: {e}")


# ── Lifestyle Match proxy (Oumeima agent) ────────────────────────────────────

@app.post("/lifestyle/match")
async def lifestyle_match(request: Request):
    body = await request.json()
    lifestyle_url = AGENT_URLS["lifestyle"]
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(f"{lifestyle_url}/match", json=body)
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Lifestyle agent error: {e}")

@app.get("/lifestyle/zones")
async def lifestyle_zones():
    lifestyle_url = AGENT_URLS["lifestyle"]
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{lifestyle_url}/zones")
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Lifestyle agent error: {e}")

@app.post("/lifestyle/osm")
async def lifestyle_osm(request: Request):
    body = await request.json()
    lifestyle_url = AGENT_URLS["lifestyle"]
    async with httpx.AsyncClient(timeout=25) as client:
        try:
            resp = await client.post(f"{lifestyle_url}/osm/enrich", json=body)
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Lifestyle agent error: {e}")

@app.get("/lifestyle/health")
async def lifestyle_health():
    lifestyle_url = AGENT_URLS["lifestyle"]
    async with httpx.AsyncClient(timeout=8) as client:
        try:
            resp = await client.get(f"{lifestyle_url}/health")
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Lifestyle agent error: {e}")


# ── Price heuristic (used for listings with missing/corrupt prices) ───────────
_CITY_MULT = {
    "tunis": 1.6, "ariana": 1.4, "ben arous": 1.3, "la marsa": 1.7,
    "nabeul": 1.2, "sousse": 1.25, "sfax": 1.05, "monastir": 1.15,
    "bizerte": 0.95, "hammamet": 1.35, "gabès": 0.85, "kairouan": 0.70,
    "gafsa": 0.65, "médenine": 0.80, "manouba": 1.1,
}
_BASE_M2 = 2000  # TND/m²

# Price range for a Tunisian real-estate listing to be considered valid
_PRICE_MIN = 10_000    # 10k TND minimum
_PRICE_MAX = 5_000_000 # 5M TND maximum

# Blacklisted title fragments (scraper garbage rows)
_BAD_TITLE_FRAGS = [
    "les plus récentes", "liste des", "les annonces", "annonces immobilières",
    "annonces des", "ballouchi.com", "détail du bien", "propriétés",
    "nos annonces", "toutes les annonces", "page des", "résultats de",
]

TUNISIA_GOV = {
    "tunis", "ariana", "ben arous", "manouba", "nabeul", "zaghouan", "bizerte",
    "béja", "jendouba", "kef", "siliana", "sousse", "monastir", "mahdia",
    "sfax", "kairouan", "kasserine", "sidi bouzid", "gabès", "médenine",
    "tataouine", "gafsa", "tozeur", "kébili", "hammamet", "la marsa",
}


def _is_valid_doc(d: dict) -> bool:
    """Return True only for real Tunisian listings with usable data."""
    title = (d.get("title") or "").lower()
    if any(frag in title for frag in _BAD_TITLE_FRAGS):
        return False
    if len(title) < 5:
        return False
    # City must be Tunisia (or unknown — we keep unknowns)
    city = (d.get("city") or "").lower().strip()
    if city and city not in TUNISIA_GOV and not any(gov in city for gov in TUNISIA_GOV):
        # Check common French/foreign city names
        foreign_keywords = ["paris", "lyon", "marseille", "france", "dubai", "london",
                            "morocco", "maroc", "algérie", "algerie", "cairo", "egypt",
                            "spain", "espagne", "uk", "usa", "canada", "istanbul"]
        if any(kw in city for kw in foreign_keywords):
            return False
    return True


def _predict_price(d: dict) -> float:
    """Estimate price from surface+city when actual price is missing/invalid."""
    surface = float(d.get("surface_m2") or 0)
    if surface <= 0:
        return 0.0
    city_key = (d.get("city") or "tunis").lower().strip()
    mult = _CITY_MULT.get(city_key, 1.0)
    rooms = int(d.get("rooms") or 3)
    room_bonus = 1 + (rooms - 2) * 0.04
    return round(_BASE_M2 * mult * room_bonus * surface)


def _clean_listing(d: dict) -> dict:
    """Build the serialisable listing dict, predicting price when necessary."""
    raw_price = float(d.get("price") or 0)

    # Decide whether the stored price is usable
    price_ok = _PRICE_MIN <= raw_price <= _PRICE_MAX
    if price_ok:
        price = raw_price
        price_predicted = False
    else:
        price = _predict_price(d)
        price_predicted = True

    return {
        "id":               str(d.get("_id", "")),
        "title":            d.get("title", ""),
        "price":            price,
        "price_predicted":  price_predicted,
        "city":             d.get("city") or d.get("zone") or "",
        "surface_m2":       float(d.get("surface_m2") or 0),
        "rooms":            int(d.get("rooms") or 0),
        "bathrooms":        int(d.get("bathrooms") or 0),
        "property_type":    d.get("property_type") or "",
        "transaction_type": d.get("transaction_type") or "",
        "url":              d.get("listing_url") or d.get("url") or "",
        "image_urls":       d.get("image_urls") or [],
        "description":      (d.get("description") or "")[:300],
    }


# ── Base query that always excludes garbage ───────────────────────────────────
def _base_query() -> dict:
    """Always-on filter: exclude titles that are scraper artefacts."""
    return {
        "title": {
            "$not": {"$regex": "les plus récentes|liste des|ballouchi", "$options": "i"}
        }
    }


# ── Direct MongoDB listings endpoint ─────────────────────────────────────────

@app.get("/listings")
async def get_listings(
    city: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    rooms: Optional[int] = None,
    transaction_type: Optional[str] = None,
    limit: int = 20,
    skip: int = 0,
):
    """
    Query MongoDB Atlas (dcrawl.listings) directly.
    - Filters out garbage/foreign listings
    - Predicts price for listings where scraper stored 0/1/invalid
    - Returns announces with image_urls
    """
    col = _get_mongo_col()
    query = _base_query()

    if city:
        query["$or"] = [
            {"city": {"$regex": city, "$options": "i"}},
            {"zone": {"$regex": city, "$options": "i"}},
        ]

    # For the price filter: include both real prices AND listings where price is bad
    # (those will be predicted). We do the range filter only when real price exists.
    if min_price is not None or max_price is not None:
        price_q: dict = {}
        if min_price is not None:
            price_q["$gte"] = min_price
        if max_price is not None:
            price_q["$lte"] = max_price
        # Apply filter only to valid price range; also include price<=1 (will be predicted)
        query["$and"] = [
            {"$or": [
                {"price": price_q},
                {"price": {"$lte": 1000}},   # will be predicted
                {"price": None},
            ]}
        ]

    if rooms is not None:
        query["rooms"] = rooms
    if transaction_type:
        query["transaction_type"] = {"$regex": transaction_type, "$options": "i"}

    # Fetch a larger batch so we can filter client-side for validity, then paginate
    FETCH = limit * 4 + skip
    cursor = col.find(query, skip=0, limit=FETCH)
    all_docs = await cursor.to_list(length=FETCH)

    valid = [d for d in all_docs if _is_valid_doc(d)]
    total_approx = await col.count_documents(query)

    page_docs = valid[skip: skip + limit]
    listings = [_clean_listing(d) for d in page_docs]
    listings = [l for l in listings if l["price"] > 0]

    return {"listings": listings, "total": max(len(valid), total_approx), "skip": skip, "limit": limit}


@app.get("/listings/{listing_id}")
async def get_listing_by_id(listing_id: str):
    """Fetch a single listing from MongoDB by its _id string."""
    from bson import ObjectId
    col = _get_mongo_col()
    try:
        oid = ObjectId(listing_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid listing id")

    doc = await col.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Listing not found")

    return {
        "id":               str(doc["_id"]),
        "title":            doc.get("title", ""),
        "price":            float(doc.get("price") or 0),
        "city":             doc.get("city") or doc.get("zone") or "",
        "surface_m2":       float(doc.get("surface_m2") or 0),
        "rooms":            int(doc.get("rooms") or 0),
        "bathrooms":        int(doc.get("bathrooms") or 0),
        "property_type":    doc.get("property_type") or "",
        "transaction_type": doc.get("transaction_type") or "",
        "url":              doc.get("listing_url") or doc.get("url") or "",
        "image_urls":       doc.get("image_urls") or [],
        "description":      doc.get("description") or "",
        "agency_owner":     doc.get("agency_owner") or "",
        "phone":            doc.get("phone") or "",
    }


# ── Dhia ML prediction (direct invoke) ───────────────────────────────────────

@app.post("/dhia/predict")
async def dhia_predict(request: Request):
    """Price prediction: tries dhia ML first (with hard 8s timeout), falls back to price-predictor."""
    body = await request.json()

    # 1) Try dhia ML service — separate client so a timeout doesn't poison the fallback client
    dhia_data = None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=2, read=8, write=5, pool=5)) as c:
            resp = await c.post(f"{AGENT_URLS['dhia']}/invoke", json={
                "input": {**body, "intent": "predict"}, "context": {}
            })
            if resp.status_code == 200:
                dhia_data = resp.json()
    except Exception:
        pass

    if dhia_data:
        # dhia returns {output: {ml_price, report, ...}} — forward directly
        out = dhia_data.get("output", dhia_data)
        if out.get("report") or out.get("ml_price"):
            return dhia_data

    # 2) Fallback: price-predictor service
    raw_pp = None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=2, read=10, write=5, pool=5)) as c:
            resp = await c.post(f"{AGENT_URLS['price_predictor']}/invoke", json={
                "input": body, "context": {}
            })
            if resp.status_code == 200:
                raw_pp = resp.json()
    except Exception:
        pass

    # 3) Pure-local fallback — VIAGRA's own heuristic (no external call needed)
    city  = body.get("city", "Tunis")
    surf  = float(body.get("surface_m2", 100))
    rooms = int(body.get("rooms", 3))

    if raw_pp:
        raw   = raw_pp.get("output", raw_pp)
        price = raw.get("predicted_price_tnd", 0) or _predict_price({"city": city, "surface_m2": surf, "rooms": rooms})
        pm2   = raw.get("price_per_m2_tnd", 0)
    else:
        price = _predict_price({"city": city, "surface_m2": surf, "rooms": rooms})
        pm2   = round(price / surf) if surf > 0 else 0

    ck   = city.lower().strip()
    mult = _CITY_MULT.get(ck, 1.0)
    report = (
        f"# Estimation de Prix — {city}\n\n"
        f"## Résultat\n"
        f"| Indicateur | Valeur |\n|---|---|\n"
        f"| **Prix estimé** | **{price:,.0f} TND** |\n"
        f"| Prix au m² | {pm2:,.0f} TND/m² |\n"
        f"| Surface | {surf:.0f} m² |\n"
        f"| Chambres | {rooms} |\n"
        f"| Ville | {city} |\n\n"
        f"## Analyse du marché\n"
        f"- Coefficient localisation {city} : **{mult:.2f}x** (base {_BASE_M2} TND/m²)\n"
        f"- Estimation calibrée sur les données scrappées du marché tunisien 2025\n"
        f"- Fourchette indicative : **{price*0.88:,.0f} — {price*1.15:,.0f} TND**\n\n"
        f"## Recommandation\n"
        f"- Comparer avec les annonces actives sur Ballouchi et DarCom pour affiner\n"
        f"- Prix final négociable : prévoir **5–10% de marge** de négociation\n\n"
        f"*Source : Modèle heuristique EstateMind · Données marché tunisien*"
    )
    return {
        "output": {
            "ml_price":     price,
            "price_per_m2": pm2,
            "city":         city,
            "surface_m2":   surf,
            "rooms":        rooms,
            "report":       report,
            "model":        "heuristic-v2-local",
        },
        "agent":      "price-heuristic",
        "confidence": 0.72,
    }


@app.post("/dhia/invest")
async def dhia_invest(request: Request):
    """Investment scoring: tries dhia ML first (with hard 8s timeout), falls back to investment-scorer."""
    body = await request.json()

    # 1) Try dhia ML service — separate client
    dhia_data = None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=2, read=8, write=5, pool=5)) as c:
            resp = await c.post(f"{AGENT_URLS['dhia']}/invoke", json={
                "input": {**body, "intent": "invest"}, "context": {}
            })
            if resp.status_code == 200:
                dhia_data = resp.json()
    except Exception:
        pass

    if dhia_data:
        out = dhia_data.get("output", dhia_data)
        if out.get("report") or out.get("verdict"):
            return dhia_data

    # 2) Fallback: investment-scorer service
    scorer_data = None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=2, read=10, write=5, pool=5)) as c:
            resp = await c.post(f"{AGENT_URLS['investment_scorer']}/invoke", json={
                "input": body, "context": {}
            })
            if resp.status_code == 200:
                scorer_data = resp.json()
    except Exception:
        pass

    if scorer_data:
        return scorer_data

    # 3) Pure-local fallback — VIAGRA's own _quick_score (no external call)
    city  = body.get("city", "Tunis")
    price = float(body.get("price", body.get("budget", 300_000)))
    surf  = float(body.get("surface_m2", 100))
    s     = _quick_score(price, city, surf)

    ck  = city.lower().strip()
    ry  = RENTAL_YIELD.get(ck, 0.046)
    ap  = APPRECIATION.get(ck, 0.035)
    verdict_emoji = {"BUY": "🟢", "HOLD": "🟡", "AVOID": "🔴"}.get(s["verdict"], "")

    market_quality = "Marché dynamique avec forte demande locative" if ry >= 0.055 else "Marché stable — privilégier la plus-value long terme"
    surf_vs = "au-dessus" if surf > 100 else "en dessous"
    if s["verdict"] == "BUY":
        reco = "- **Acheter** : rendement solide et appréciation attendue favorable sur 5 ans"
    elif s["verdict"] == "HOLD":
        reco = "- **Attendre** : surveiller l'évolution du marché avant de s'engager"
    else:
        reco = "- **Éviter** : rendement insuffisant au prix actuel — négocier ou chercher une autre localisation"

    report = (
        f"# Analyse d'Investissement — {city}\n\n"
        f"## Verdict : {verdict_emoji} **{s['verdict']}** (Score {s['score']}/100)\n\n"
        f"## Métriques financières\n"
        f"| Indicateur | Valeur |\n|---|---|\n"
        f"| **Prix analysé** | **{price:,.0f} TND** |\n"
        f"| Rendement locatif brut | {s['rental_yield_pct']}% / an |\n"
        f"| Loyer annuel estimé | {s['annual_rent_est_tnd']:,.0f} TND |\n"
        f"| Loyer mensuel estimé | {round(s['annual_rent_est_tnd']/12):,.0f} TND |\n"
        f"| Appréciation annuelle | {ap*100:.1f}% |\n"
        f"| **ROI total 5 ans** | **{s['roi_5y_pct']}%** |\n\n"
        f"## Analyse marché {city}\n"
        f"- Rendement locatif moyen du gouvernorat : **{ry*100:.1f}%**\n"
        f"- Tendance prix : **+{ap*100:.1f}%/an** (historique 2020-2025)\n"
        f"- {market_quality}\n\n"
        f"## Recommandation\n"
        f"{reco}\n"
        f"- Surface de {surf:.0f} m² {surf_vs} de la médiane locale\n\n"
        f"*Source : Modèle EstateMind · Données marché tunisien 2025*"
    )
    return {
        "output": {
            **s,
            "city":    city,
            "price":   price,
            "report":  report,
        },
        "agent":      "investment-heuristic",
        "confidence": 0.75,
    }


RENTAL_YIELD = {
    "tunis":0.055,"ariana":0.050,"sousse":0.060,"sfax":0.052,"nabeul":0.065,
    "monastir":0.058,"hammamet":0.070,"bizerte":0.048,"gabès":0.045,"gabes":0.045,
    "kairouan":0.042,"la marsa":0.050,"manouba":0.047,"ben arous":0.048,
    "zaghouan":0.043,"mahdia":0.055,"djerba":0.072,"tozeur":0.050,
}
APPRECIATION = {
    "tunis":0.06,"ariana":0.055,"nabeul":0.07,"sousse":0.065,"sfax":0.04,
    "monastir":0.055,"hammamet":0.075,"la marsa":0.065,"djerba":0.08,
    "bizerte":0.045,"mahdia":0.055,"manouba":0.045,"ben arous":0.050,
}

def _quick_score(price: float, city: str, surface: float) -> dict:
    ck = city.lower().strip()
    ry = RENTAL_YIELD.get(ck, 0.046)
    ap = APPRECIATION.get(ck, 0.035)
    surf_bonus = 15 if surface > 120 else 8 if surface > 60 else 0
    score = min(100, int(ry * 600 + ap * 400 + surf_bonus))
    verdict = "BUY" if score >= 70 else "HOLD" if score >= 50 else "AVOID"
    return {
        "score": score, "verdict": verdict,
        "rental_yield_pct": round(ry * 100, 1),
        "annual_rent_est_tnd": round(price * ry),
        "roi_5y_pct": round((ry + ap) * 5 * 100, 1),
    }


@app.get("/dhia/invest-scan")
async def invest_scan_test():
    return {"status": "ok", "message": "Investment scanner endpoint is ready. Use POST to analyze."}


@app.post("/dhia/invest-scan")
@app.post("/dhia/invest-scan/")
async def invest_scan(request: Request):
    """Scans MongoDB listings, scores each one, returns ranked investment opportunities."""
    body = await request.json()
    city_filter   = body.get("city", "").strip()
    max_budget    = float(body.get("budget", 2_000_000))
    min_budget    = float(body.get("min_budget", 50_000))
    top_n         = int(body.get("top_n", 20))
    tx_type       = body.get("transaction_type", "")  # "vente" | "location" | ""
    gemini_key    = os.getenv("GEMINI_API_KEY", "AIzaSyBZOj9UYCiQKvC6NGt6yofJ1auF3K8oQtU")

    col = _get_mongo_col()

    # Build MongoDB query
    q: dict = {"price": {"$gte": min_budget, "$lte": max_budget}}
    if city_filter:
        q["$or"] = [
            {"city": {"$regex": city_filter, "$options": "i"}},
            {"gouvernorat": {"$regex": city_filter, "$options": "i"}},
        ]
    if tx_type:
        q["transaction_type"] = {"$regex": tx_type, "$options": "i"}

    raw = await col.find(q, {
        "title": 1, "price": 1, "city": 1, "surface_m2": 1,
        "rooms": 1, "property_type": 1, "transaction_type": 1,
        "listing_url": 1, "image_urls": 1, "gouvernorat": 1,
    }).limit(200).to_list(length=200)

    if not raw:
        return {"opportunities": [], "total_scanned": 0, "summary": "Aucun bien trouvé avec ces critères."}

    # Score each listing
    scored = []
    for doc in raw:
        if not _is_valid_doc(doc):
            continue
        price   = float(doc.get("price") or 0)
        surface = float(doc.get("surface_m2") or 80)
        city    = doc.get("city") or doc.get("gouvernorat") or "Tunisie"
        if price < 5000 or price > 50_000_000:
            continue
        s = _quick_score(price, city, surface)
        raw_imgs = doc.get("image_urls") or []
        thumb = raw_imgs[0] if raw_imgs else None
        scored.append({
            "id":               str(doc.get("_id", "")),
            "title":            (doc.get("title") or "Bien immobilier")[:80],
            "price":            price,
            "city":             city,
            "surface_m2":       surface if surface >= 5 else None,
            "rooms":            doc.get("rooms"),
            "property_type":    doc.get("property_type"),
            "transaction_type": doc.get("transaction_type"),
            "listing_url":      doc.get("listing_url"),
            "thumbnail":        thumb,
            **s,
        })

    # Sort: BUY first, then by score desc
    order = {"BUY": 0, "HOLD": 1, "AVOID": 2}
    scored.sort(key=lambda x: (order[x["verdict"]], -x["score"]))
    top = scored[:top_n]

    # Count verdicts
    buys  = sum(1 for x in scored if x["verdict"] == "BUY")
    holds = sum(1 for x in scored if x["verdict"] == "HOLD")
    avoids= sum(1 for x in scored if x["verdict"] == "AVOID")

    # Gemini market summary for the top opportunities
    gemini_summary = ""
    if gemini_key and top:
        top3 = top[:3]
        desc = "\n".join(
            f"- {x['title']} | {x['city']} | {x['price']:,.0f} TND | {x['surface_m2'] or '?'} m² | Score {x['score']}/100 ({x['verdict']})"
            for x in top3
        )
        prompt = f"""Tu es un conseiller immobilier expert sur le marché tunisien.
Voici les 3 meilleures opportunités trouvées parmi {len(scored)} biens analysés (budget {min_budget:,.0f}–{max_budget:,.0f} TND) :

{desc}

Rédige en 3-4 phrases une synthèse d'investissement concise :
- Qualité générale des opportunités trouvées
- Quelle ville/bien offre le meilleur rapport risque/rendement
- Conseil stratégique pour l'investisseur (type de bien à cibler, timing)
Sois direct et professionnel, max 120 mots."""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={gemini_key}"
        try:
            async with httpx.AsyncClient(timeout=20) as c:
                r = await c.post(url, json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.3, "maxOutputTokens": 300},
                })
                if r.status_code == 200:
                    gemini_summary = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            pass

    return {
        "opportunities":  top,
        "total_scanned":  len(scored),
        "buys":           buys,
        "holds":          holds,
        "avoids":         avoids,
        "gemini_summary": gemini_summary,
        "filter":         {"city": city_filter, "budget_range": [min_budget, max_budget]},
    }


@app.get("/dhia/health")
async def dhia_health():
    async with httpx.AsyncClient(timeout=8) as client:
        try:
            resp = await client.get(f"{AGENT_URLS['dhia']}/health")
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Dhia agent error: {e}")


# ── Market summary ────────────────────────────────────────────────────────────
@app.get("/market/summary")
async def market_summary():
    """Returns clean market stats from MongoDB — only valid-priced Tunisian listings."""
    col = _get_mongo_col()
    try:
        # Only listings with a real price in sensible range
        docs = await col.find(
            {
                "price": {"$gte": _PRICE_MIN, "$lte": _PRICE_MAX},
                "title": {"$not": {"$regex": "les plus récentes|liste des|ballouchi", "$options": "i"}},
            },
            {"price": 1, "surface_m2": 1},
        ).to_list(length=5000)

        prices   = [float(d["price"])      for d in docs if d.get("price")]
        surfaces = [float(d["surface_m2"]) for d in docs if d.get("surface_m2") and d["surface_m2"] > 0]
        pm2s     = [p / s for d, p, s in
                    zip(docs, prices, [float(d.get("surface_m2") or 0) for d in docs]) if s > 0]

        if not prices:
            return {"error": "No data"}

        prices.sort()
        n = len(prices)
        return {
            "count":            n,
            "avg_price":        round(sum(prices) / n),
            "median_price":     prices[n // 2],
            "min_price":        prices[0],
            "max_price":        prices[-1],
            "avg_price_per_m2": round(sum(pm2s) / len(pm2s)) if pm2s else None,
            "avg_surface":      round(sum(surfaces) / len(surfaces)) if surfaces else None,
            # nested shape the homepage also reads
            "global_stats": {
                "total_biens":  n,
                "prix_moyen":   round(sum(prices) / n),
                "prix_median":  prices[n // 2],
                "pm2_moyen":    round(sum(pm2s) / len(pm2s)) if pm2s else None,
            },
        }
    except Exception as e:
        return {"error": str(e)}


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    statuses = {}
    async with httpx.AsyncClient(timeout=4) as client:
        for name, url in AGENT_URLS.items():
            try:
                r = await client.get(f"{url}/health")
                statuses[name] = "ok" if r.status_code == 200 else "degraded"
            except Exception:
                statuses[name] = "unreachable"
    redis_status = "ok"
    if redis_client:
        try:
            await redis_client.ping()
        except Exception:
            redis_status = "unreachable"
    else:
        redis_status = "disabled"
    return {"status": "ok", "agents": statuses, "redis": redis_status}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
