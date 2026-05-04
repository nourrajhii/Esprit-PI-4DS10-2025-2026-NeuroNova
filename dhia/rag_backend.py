"""
==============================================================================
EstateMind | Optimized Dual-Agent RAG System (FastAPI Backend)
==============================================================================
"""

import os
import json
import joblib
import pandas as pd
import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

MODEL_PATH = "models/price_model.joblib"
META_PATH  = "models/model_metadata.json"
DATA_PATH  = "ai_enhanced_listings.csv"
NEW_DATA_PATH = "Property-Prices-in-Tunisia.csv"

# ---------------------------------------------------------------------------
# DETERMINISTIC DATA RETRIEVAL (Token-Optimized RAG)
# ---------------------------------------------------------------------------

def get_similar_listings(city, surface, limit=3):
    """Retrieves top 3 similar properties from DB 1 to save tokens."""
    try:
        df = pd.read_csv(DATA_PATH)
        similar = df[(df['city'] == city) & (df['inferred_type'] == 'vente')]
        similar['surface_diff'] = abs(similar['surface_m2'] - surface)
        return similar.sort_values('surface_diff').head(limit)[['title', 'price', 'surface_m2']].to_dict('records')
    except Exception:
        return []

def get_new_data_context(city, surface, limit=3):
    """Retrieves top 3 similar properties from the NEW dataset."""
    try:
        df = pd.read_csv(NEW_DATA_PATH)
        # category,room_count,bathroom_count,size,type,price,city,region,log_price
        similar = df[(df['city'] == city) & (df['type'] == 'À Vendre')]
        similar['surface_diff'] = abs(similar['size'] - surface)
        res = similar.sort_values('surface_diff').head(limit)[['category', 'price', 'size', 'region']].to_dict('records')
        return res
    except Exception as e:
        print(f"Error loading new data: {e}")
        return []

def get_deal_context(budget, city=None):
    try:
        df = pd.read_csv(DATA_PATH)
        query = (df['inferred_type'] == 'vente') & (df['price'] <= budget) & (df['is_duplicate'] == False)
        if city and str(city).strip():
            query &= (df['city'].str.contains(city, case=False, na=False))
            
        deals = df[query].sort_values(['deal_score_pct', 'annual_roi_pct'], ascending=False).head(3)
        
        # Fallback: if no deals are found in the specific city, find deals anywhere in Tunisia within budget
        if deals.empty and city and str(city).strip():
            fallback_query = (df['inferred_type'] == 'vente') & (df['price'] <= budget) & (df['is_duplicate'] == False)
            deals = df[fallback_query].sort_values(['deal_score_pct', 'annual_roi_pct'], ascending=False).head(3)

        return deals[['title', 'city', 'price', 'deal_score_pct', 'annual_roi_pct']].to_dict('records')
    except Exception as e:
        print(f"Error in deal context: {e}")
        return []

def run_ml_prediction(surface_m2, rooms, bathrooms, city_tier):
    try:
        model = joblib.load(MODEL_PATH)
        with open(META_PATH, 'r') as f:
            meta = json.load(f)
        features = {
            "surface_m2": surface_m2, "log_surface": np.log1p(surface_m2),
            "rooms": rooms, "bathrooms": bathrooms, "total_rooms": rooms + bathrooms,
            "rooms_per_m2": rooms / surface_m2 if surface_m2 > 0 else 0,
            "city_tier": city_tier, "prop_tier": 3, "is_sale": 1, "is_apartment": 1, "is_villa": 0, "is_studio": 0, "city_encoded": 0
        }
        X = pd.DataFrame([features]).reindex(columns=meta['features'], fill_value=0)
        log_price = model.predict(X)[0]
        return float(np.expm1(log_price))
    except Exception:
        return 0

# ---------------------------------------------------------------------------
# AGENT LOGIC (One-Shot Prompts to save tokens)
# ---------------------------------------------------------------------------

def run_prediction_agent(city, surface, rooms, baths, tier):
    ml_price = run_ml_prediction(surface, rooms, baths, tier)
    db1_data = get_similar_listings(city, surface, 3)
    db2_data = get_new_data_context(city, surface, 3)
    
    prompt = f"""
    You are the 'EstateMind Pricing Agent'. I need a DUAL-VALUATION REPORT.
    Property Details: {surface}m2, {rooms} rooms, {baths} baths in {city} (Tier {tier}).
    
    Data Source 1 (ML Raw Output): {ml_price:,.0f} 
    Data Source 2 (Similar Active Listings): {db1_data}
    Data Source 3 (Historical Market Data): {db2_data}
    
    CRITICAL INSTRUCTIONS:
    1. PROVIDE TWO DISTINCT PRICES: 
       - An 'Estimated Acquisition Cost' (Sale Price in TND).
       - An 'Estimated Monthly Rental Value' (Rent in TND/month).
    2. The ML Raw Output might be skewed. Use the 'Similar Active Listings' and 'Historical Market Data' to intelligently adjust the final numbers. 
    3. If the property is large (e.g. >200m2) and the ML Output is low (e.g. <5000), recognize that the ML might be predicting RENT, not SALE.
    4. Write a comprehensive report on the market dynamics in {city}.
    5. Discuss the macroeconomic context: Land banking vs. Current yields.
    
    Format the output beautifully in markdown. Highlighting the two price vectors clearly at the top.
    """
    model = genai.GenerativeModel('models/gemini-flash-latest')
    response = model.generate_content(prompt)
    return {
        "ml_price": ml_price,
        "report": response.text
    }

def run_investment_agent(budget, city):
    deals = get_deal_context(budget, city)
    
    prompt = f"""
    You are the 'EstateMind Investment Strategist'. I have a total budget of {budget:,.0f} TND.
    Target Region: {city if city else 'All Tunisia'}
    
    Live Scraped Opportunities from our DB: {deals}
    
    GOAL: Use the {budget:,.0f} TND budget TO THE FULLEST. 
    
    TASK:
    1. EVALUATE the deals. If the budget is large (e.g. 500k TND) and individual deals are small (e.g. 200k TND), YOU SHOULD SUGGEST A COMBINED PORTFOLIO (e.g. "Buy Deal A AND Deal B").
    2. PROVIDE A CLEAR & CONVINCING FINAL VERDICT. Be decisive. Do not say "it depends". Tell the user exactly what to buy and why.
    3. QUOTE THE EXACT DATA: Title, Price, Deal Score, and ROI from the provided list.
    4. ANALYZE RISK: Explain why this specific allocation of the {budget} TND is safer/better than other options.
    5. VERDICT: End with a "FINAL INVESTMENT ACTION" section.
    
    Format in high-quality professional markdown. Use tables or lists for clarity.
    """
    model = genai.GenerativeModel('models/gemini-flash-latest')
    response = model.generate_content(prompt)
    return {
        "deals": deals,
        "report": response.text
    }
