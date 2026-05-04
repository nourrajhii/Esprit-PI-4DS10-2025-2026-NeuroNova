"""
services/lifestyle-match/main.py
ImmoMatch AI — Lifestyle Match & Community Intelligence
FastAPI service wrapping Oumeima's agent logic.
Port: 8010
"""
import re, math, json
from typing import List, Optional
from pathlib import Path

import numpy as np
import requests as _req
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="ImmoMatch Lifestyle Agent", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Zone data (OSM-calibrated, from Oumeima) ──────────────────────────────────
ZONE_OSM = {
    'Chotrana / La Soukra': {'schools_count':8,'shops_count':15,'transport_count':4,'green_spaces_count':3,'nightlife_count':1,'arterial_roads_count':2,'premium_market_score':7,'health_count':3,'parking_count':5},
    'La Marsa':             {'schools_count':7,'shops_count':18,'transport_count':5,'green_spaces_count':4,'nightlife_count':4,'arterial_roads_count':3,'premium_market_score':9,'health_count':5,'parking_count':6},
    'Sidi Bou Said':        {'schools_count':4,'shops_count':9, 'transport_count':3,'green_spaces_count':5,'nightlife_count':3,'arterial_roads_count':2,'premium_market_score':9,'health_count':2,'parking_count':4},
    'Les Berges du Lac':    {'schools_count':6,'shops_count':22,'transport_count':8,'green_spaces_count':2,'nightlife_count':4,'arterial_roads_count':4,'premium_market_score':10,'health_count':6,'parking_count':8},
    'El Manar':             {'schools_count':9,'shops_count':14,'transport_count':8,'green_spaces_count':2,'nightlife_count':2,'arterial_roads_count':5,'premium_market_score':6,'health_count':4,'parking_count':5},
    'Menzah':               {'schools_count':8,'shops_count':16,'transport_count':7,'green_spaces_count':3,'nightlife_count':2,'arterial_roads_count':4,'premium_market_score':7,'health_count':5,'parking_count':6},
    'Ennasr':               {'schools_count':7,'shops_count':19,'transport_count':8,'green_spaces_count':2,'nightlife_count':3,'arterial_roads_count':4,'premium_market_score':7,'health_count':5,'parking_count':7},
    'Carthage':             {'schools_count':5,'shops_count':10,'transport_count':4,'green_spaces_count':4,'nightlife_count':2,'arterial_roads_count':3,'premium_market_score':9,'health_count':3,'parking_count':4},
    'Gammarth':             {'schools_count':4,'shops_count':11,'transport_count':3,'green_spaces_count':5,'nightlife_count':3,'arterial_roads_count':2,'premium_market_score':8,'health_count':2,'parking_count':3},
    'Bardo':                {'schools_count':6,'shops_count':16,'transport_count':9,'green_spaces_count':1,'nightlife_count':2,'arterial_roads_count':6,'premium_market_score':4,'health_count':4,'parking_count':5},
    'Ben Arous':            {'schools_count':5,'shops_count':13,'transport_count':6,'green_spaces_count':1,'nightlife_count':1,'arterial_roads_count':5,'premium_market_score':4,'health_count':3,'parking_count':4},
    'Centre Tunis':         {'schools_count':6,'shops_count':24,'transport_count':10,'green_spaces_count':1,'nightlife_count':5,'arterial_roads_count':7,'premium_market_score':6,'health_count':7,'parking_count':6},
    'Ariana Ville':         {'schools_count':6,'shops_count':15,'transport_count':8,'green_spaces_count':2,'nightlife_count':2,'arterial_roads_count':5,'premium_market_score':5,'health_count':4,'parking_count':5},
    'Autre':                {'schools_count':4,'shops_count':10,'transport_count':5,'green_spaces_count':2,'nightlife_count':2,'arterial_roads_count':4,'premium_market_score':5,'health_count':3,'parking_count':4},
}

ZONE_COORDS = {
    'Chotrana / La Soukra': (36.889, 10.193),
    'La Marsa':             (36.877, 10.325),
    'Sidi Bou Said':        (36.870, 10.341),
    'Les Berges du Lac':    (36.848, 10.229),
    'El Manar':             (36.852, 10.183),
    'Menzah':               (36.853, 10.183),
    'Ennasr':               (36.859, 10.191),
    'Carthage':             (36.859, 10.329),
    'Gammarth':             (36.901, 10.288),
    'Bardo':                (36.810, 10.146),
    'Ben Arous':            (36.753, 10.229),
    'Centre Tunis':         (36.819, 10.178),
    'Ariana Ville':         (36.862, 10.196),
    'Autre':                (36.820, 10.180),
}

# ── Score derivation ──────────────────────────────────────────────────────────
def _clamp(x, lo=0, hi=100):
    return max(lo, min(hi, round(float(x), 2)))

def _scaled(count, max_count):
    return _clamp((count / max_count) * 100)

def derive_scores(osm: dict) -> dict:
    schools_score   = _scaled(osm['schools_count'], 10)
    shops_score     = _scaled(osm['shops_count'], 25)
    transport_score = _scaled(osm['transport_count'], 10)
    green_score     = _scaled(osm['green_spaces_count'], 6)
    health_score    = _scaled(osm['health_count'], 7)
    parking_score   = _scaled(osm['parking_count'], 8)
    calm_score_est  = _clamp(72 + osm['green_spaces_count']*4
                             - osm['arterial_roads_count']*7
                             - osm['nightlife_count']*5)
    safety_score_est = _clamp(52 + osm['green_spaces_count']*3
                              + osm['premium_market_score']*3
                              + osm['health_count']*2
                              - osm['nightlife_count']*2
                              - osm['arterial_roads_count']*2)
    invest_score_est = _clamp(30 + osm['premium_market_score']*6
                              + osm['shops_count']*1.0
                              + osm['transport_count']*1.5)
    return {
        'schools_score':    schools_score,
        'shops_score':      shops_score,
        'transport_score':  transport_score,
        'green_score':      green_score,
        'health_score':     health_score,
        'parking_score':    parking_score,
        'calm_score_est':   calm_score_est,
        'safety_score_est': safety_score_est,
        'invest_score_est': invest_score_est,
    }

# Pre-compute zone scores
ZONE_SCORES = {zone: derive_scores(osm) for zone, osm in ZONE_OSM.items()}

# ── Profile weights ───────────────────────────────────────────────────────────
PROFILE_WEIGHTS = {
    'family':    {'safety_score_est':0.22,'calm_score_est':0.18,'schools_score':0.24,'shops_score':0.12,'transport_score':0.08,'invest_score_est':0.08,'green_score':0.08},
    'young_pro': {'safety_score_est':0.12,'calm_score_est':0.05,'schools_score':0.04,'shops_score':0.21,'transport_score':0.24,'invest_score_est':0.20,'green_score':0.14},
    'investor':  {'safety_score_est':0.10,'calm_score_est':0.06,'schools_score':0.04,'shops_score':0.13,'transport_score':0.14,'invest_score_est':0.43,'green_score':0.10},
    'student':   {'safety_score_est':0.15,'calm_score_est':0.08,'schools_score':0.22,'shops_score':0.16,'transport_score':0.24,'invest_score_est':0.05,'green_score':0.10},
    'retired':   {'safety_score_est':0.28,'calm_score_est':0.30,'schools_score':0.05,'shops_score':0.15,'transport_score':0.08,'invest_score_est':0.06,'green_score':0.08},
}

# ── Profile parser ────────────────────────────────────────────────────────────
def parse_profile(text: str) -> dict:
    t = text.lower()

    if any(w in t for w in ['famille','enfant','bébé','mari','femme','school','kids','child']):
        lifestyle = 'family'
    elif any(w in t for w in ['étudiant','université','campus','student','fac']):
        lifestyle = 'student'
    elif any(w in t for w in ['invest','rendement','locatif','rentabilit','yield','rental']):
        lifestyle = 'investor'
    elif any(w in t for w in ['retraité','calme','tranquille','retiré','senior','pensionnaire']):
        lifestyle = 'retired'
    else:
        lifestyle = 'young_pro'

    m = re.search(r'(\d[\d\s]*)\s*(?:k(?:DT|dt|\b)|dt|dinar|tnd)', t)
    if m:
        raw = int(re.sub(r'\s', '', m.group(1)))
        if re.search(r'\d+\s*k', t) and raw < 5000:
            raw *= 1000
        budget = raw
    else:
        budget = {'family':450000,'young_pro':300000,'student':180000,'investor':500000,'retired':400000}[lifestyle]

    if any(w in t for w in ['sécurité','sécurisé','sûr','calme','tranquille','safe','quiet']):
        priority = 'safety'
    elif any(w in t for w in ['transport','métro','bus','tramway','mobil']):
        priority = 'transport'
    elif any(w in t for w in ['école','lycée','collège','crèche','university']):
        priority = 'schools'
    elif any(w in t for w in ['commerc','shop','restaurant','marché','animé']):
        priority = 'amenities'
    elif any(w in t for w in ['invest','rentabilit','rendement','plus-value']):
        priority = 'investment'
    else:
        priority = {'family':'schools','young_pro':'transport','student':'transport','investor':'investment','retired':'safety'}[lifestyle]

    weights = dict(PROFILE_WEIGHTS[lifestyle])
    prio_map = {'safety':'safety_score_est','transport':'transport_score','schools':'schools_score','amenities':'shops_score','investment':'invest_score_est'}
    boost_key = prio_map.get(priority)
    if boost_key and boost_key in weights:
        weights[boost_key] = min(weights[boost_key] + 0.10, 1.0)
        total = sum(weights.values())
        weights = {k: v/total for k,v in weights.items()}

    return {'lifestyle': lifestyle, 'budget': budget, 'priority': priority, 'weights': weights}

# ── Zone-level matching ───────────────────────────────────────────────────────
def zone_match_scores(weights: dict) -> List[dict]:
    results = []
    for zone, scores in ZONE_SCORES.items():
        match_score = round(sum(scores[k] * w for k, w in weights.items() if k in scores), 1)
        lat, lon = ZONE_COORDS.get(zone, (36.82, 10.18))
        results.append({
            'zone':          zone,
            'match_score':   match_score,
            'lat':           lat,
            'lon':           lon,
            'scores':        {k: round(v, 1) for k, v in scores.items()},
            'osm':           ZONE_OSM[zone],
        })
    results.sort(key=lambda x: x['match_score'], reverse=True)
    return results

# ── Listing data ──────────────────────────────────────────────────────────────
def _load_listings():
    candidates = [
        Path('/app/data/ai_ready_listings_clean.csv'),
        Path('/app/data/ai_ready_listings.csv'),
        Path('data/ai_ready_listings_clean.csv'),
    ]
    for p in candidates:
        if p.exists():
            try:
                import pandas as pd
                df = pd.read_csv(p)
                df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
                for col in ['title','price','city','surface_m2','rooms','transaction_type','url']:
                    if col not in df.columns:
                        df[col] = None
                return df
            except Exception:
                pass
    return None

def _detect_zone(title: str) -> str:
    ZONE_PATTERNS = [
        ('Chotrana / La Soukra', r'chotrana|soukra'),
        ('La Marsa',             r'\bmarsa\b'),
        ('Sidi Bou Said',        r'sidi bou|sidi-bou'),
        ('Les Berges du Lac',    r'berges|\blac\b'),
        ('El Manar',             r'manar'),
        ('Menzah',               r'menzah'),
        ('Ennasr',               r'ennasr|ennaser|\bnasr\b'),
        ('Carthage',             r'carthage'),
        ('Gammarth',             r'gammarth'),
        ('Bardo',                r'\bbardo\b'),
        ('Ben Arous',            r'ben arous|megrine'),
        ('Centre Tunis',         r'centre|medina|belv'),
        ('Ariana Ville',         r'\bariana\b'),
    ]
    t = str(title).lower()
    for zone, pat in ZONE_PATTERNS:
        if re.search(pat, t):
            return zone
    return 'Autre'

def match_listings(weights: dict, budget: int, top_n: int = 10) -> List[dict]:
    df = _load_listings()
    if df is None:
        return []

    import pandas as pd
    df = df.copy()
    df['price']      = pd.to_numeric(df['price'], errors='coerce')
    df['surface_m2'] = pd.to_numeric(df['surface_m2'], errors='coerce')
    df['zone_label'] = df['title'].fillna('').apply(_detect_zone)

    # Merge zone scores
    for col, scores in ZONE_SCORES.items():
        pass
    def get_score(zone, key):
        return ZONE_SCORES.get(zone, ZONE_SCORES['Autre']).get(key, 0)

    df['match_score'] = df['zone_label'].apply(
        lambda z: round(sum(get_score(z, k) * w for k, w in weights.items()), 1)
    )
    df['lat'] = df['zone_label'].apply(lambda z: ZONE_COORDS.get(z, (36.82, 10.18))[0])
    df['lon'] = df['zone_label'].apply(lambda z: ZONE_COORDS.get(z, (36.82, 10.18))[1])

    # Budget filter
    if budget > 50_000:
        mask = df['transaction_type'].fillna('').str.lower().isin(['vente','sale','à vendre'])
        if mask.sum() >= 5:
            df = df[mask]
        df = df[df['price'].fillna(999e9) <= budget * 1.3]
    else:
        mask = df['transaction_type'].fillna('').str.lower().isin(['location','louer','à louer'])
        if mask.sum() >= 5:
            df = df[mask]
        df = df[df['price'].fillna(999e9) <= budget * 2]

    if len(df) == 0:
        df = _load_listings().copy()
        df['price']      = pd.to_numeric(df['price'], errors='coerce')
        df['surface_m2'] = pd.to_numeric(df['surface_m2'], errors='coerce')
        df['zone_label'] = df['title'].fillna('').apply(_detect_zone)
        df['match_score'] = df['zone_label'].apply(
            lambda z: round(sum(get_score(z, k) * w for k, w in weights.items()), 1)
        )
        df['lat'] = df['zone_label'].apply(lambda z: ZONE_COORDS.get(z, (36.82, 10.18))[0])
        df['lon'] = df['zone_label'].apply(lambda z: ZONE_COORDS.get(z, (36.82, 10.18))[1])

    top = df.nlargest(top_n, 'match_score')
    listings = []
    for _, row in top.iterrows():
        listings.append({
            'title':            str(row.get('title', ''))[:80],
            'zone':             str(row.get('zone_label', 'Autre')),
            'price':            float(row['price']) if row['price'] == row['price'] else None,
            'surface_m2':       float(row['surface_m2']) if row['surface_m2'] == row['surface_m2'] else None,
            'transaction_type': str(row.get('transaction_type', '')),
            'url':              str(row.get('url', '')) if row.get('url') else None,
            'match_score':      float(row['match_score']),
            'lat':              float(row['lat']),
            'lon':              float(row['lon']),
        })
    return listings

# ── OSM live enrichment (optional) ───────────────────────────────────────────
OVERPASS_URL = 'https://overpass-api.de/api/interpreter'

def fetch_osm_live(lat: float, lon: float, radius: int = 800) -> Optional[dict]:
    query = f"""
    [out:json][timeout:20];
    (
      node["amenity"~"school|kindergarten|university|college"](around:{radius},{lat},{lon});
      node["amenity"~"hospital|pharmacy|clinic|dentist"](around:{radius},{lat},{lon});
      node["shop"~"supermarket|convenience|bakery|butcher|mall"](around:{radius},{lat},{lon});
      node["amenity"~"restaurant|cafe|fast_food|bar|pub"](around:{radius},{lat},{lon});
      node["public_transport"="stop_position"](around:{radius},{lat},{lon});
      node["leisure"~"park|garden|playground|sports_centre"](around:{radius},{lat},{lon});
      node["amenity"="parking"](around:{radius},{lat},{lon});
      way["highway"~"primary|secondary|tertiary"](around:{radius},{lat},{lon});
    );
    out body;
    """
    try:
        r = _req.post(OVERPASS_URL, data={'data': query}, timeout=20)
        if r.status_code != 200:
            return None
        elements = r.json().get('elements', [])
        def count(tag, vals):
            return sum(1 for e in elements if e.get('tags', {}).get(tag) in vals)
        return {
            'schools_count':        count('amenity', ['school','kindergarten','university','college']),
            'health_count':         count('amenity', ['hospital','pharmacy','clinic','dentist']),
            'shops_count':          count('shop', ['supermarket','convenience','bakery','butcher','mall'])
                                    + count('amenity', ['restaurant','cafe','fast_food','bar','pub']),
            'transport_count':      count('public_transport', ['stop_position']),
            'green_spaces_count':   count('leisure', ['park','garden','playground','sports_centre']),
            'nightlife_count':      count('amenity', ['restaurant','cafe','fast_food','bar','pub']),
            'parking_count':        count('amenity', ['parking']),
            'arterial_roads_count': sum(1 for e in elements if e.get('type')=='way' and e.get('tags',{}).get('highway') in ['primary','secondary','tertiary']),
            'premium_market_score': 5,
            'total_amenities':      len(elements),
        }
    except Exception:
        return None

# ── Request / Response models ─────────────────────────────────────────────────
class MatchRequest(BaseModel):
    prompt: str
    top_n: int = 10

class ZoneOSMRequest(BaseModel):
    lat: float
    lon: float
    radius: int = 800

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "lifestyle-match"}

@app.post("/match")
def match(req: MatchRequest):
    if not req.prompt.strip():
        raise HTTPException(400, "prompt is required")

    profile = parse_profile(req.prompt)
    zones   = zone_match_scores(profile['weights'])
    listings = match_listings(profile['weights'], profile['budget'], req.top_n)

    # Zone summary for top 5
    top_zones = zones[:5]

    return {
        "profile": {
            "lifestyle": profile['lifestyle'],
            "budget":    profile['budget'],
            "priority":  profile['priority'],
        },
        "zones":    zones,          # all 14 zones with scores + coords
        "top_zones": top_zones,
        "listings": listings,       # real listings if CSV available, else []
        "has_listings": len(listings) > 0,
    }

@app.get("/zones")
def get_zones():
    zones = []
    for zone, scores in ZONE_SCORES.items():
        lat, lon = ZONE_COORDS.get(zone, (36.82, 10.18))
        zones.append({
            'zone':   zone,
            'lat':    lat,
            'lon':    lon,
            'scores': {k: round(v, 1) for k, v in scores.items()},
            'osm':    ZONE_OSM[zone],
        })
    return {"zones": zones}

@app.post("/osm/enrich")
def osm_enrich(req: ZoneOSMRequest):
    live = fetch_osm_live(req.lat, req.lon, req.radius)
    if live:
        scores = derive_scores(live)
        return {"source": "live", "osm": live, "scores": {k: round(v,1) for k,v in scores.items()}}
    # fallback: find nearest zone
    best_zone = min(ZONE_COORDS, key=lambda z: math.dist(ZONE_COORDS[z], (req.lat, req.lon)))
    return {
        "source":  "cached",
        "zone":    best_zone,
        "osm":     ZONE_OSM[best_zone],
        "scores":  {k: round(v,1) for k,v in ZONE_SCORES[best_zone].items()},
    }

@app.get("/profiles")
def get_profiles():
    return {"profiles": list(PROFILE_WEIGHTS.keys()), "weights": PROFILE_WEIGHTS}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
