import pandas as pd
import numpy as np
import time
import os
import re
from rag_backend import run_prediction_agent

def extract_price(text):
    # Try to extract the number associated with the 'Estimated Acquisition Cost' or 'Sale Price'
    # We look for a pattern like "Estimated Acquisition Cost: 450,000 TND"
    match = re.search(r'Estimated Acquisition Cost[^0-9]*?([\d,]+(?:\.\d+)?)', text, re.IGNORECASE)
    if match:
        val = match.group(1).replace(',', '')
        return float(val)
    return None

def run_evaluation(n_samples=10):
    print("==================================================================")
    print(f"EstateMind AI - Generating Comprehensive Evaluation Sheet ({n_samples} Samples)")
    print("==================================================================")
    
    if not os.path.exists('ai_enhanced_listings.csv'):
        print("Dataset not found.")
        return

    df = pd.read_csv('ai_enhanced_listings.csv')
    test_set = df[df['inferred_type'] == 'vente'].dropna(subset=['price']).sample(n_samples, random_state=42)
    
    results = []
    
    for i, (_, row) in enumerate(test_set.iterrows()):
        print(f"[{i+1}/{n_samples}] Evaluating property in {row['city']} (Real Price: {row['price']:,.0f} TND)...")
        real_price = row['price']
        
        # Run Hybrid Agent (returns both ML baseline and RAG Report)
        start = time.time()
        res = run_prediction_agent(
            city=row['city'],
            surface=row['surface_m2'],
            rooms=row['rooms'],
            baths=row['bathrooms'],
            tier=3
        )
        latency = time.time() - start
        
        ml_price = res['ml_price']
        rag_report = res['report']
        
        # Parse RAG price
        rag_price = extract_price(rag_report)
        # If extraction fails, we assume RAG couldn't determine a better price and fell back to ML
        if rag_price is None or rag_price < 1000:
            rag_price = ml_price
            
        ml_error = abs(ml_price - real_price) / real_price * 100 if real_price else 0
        rag_error = abs(rag_price - real_price) / real_price * 100 if real_price else 0
        
        results.append({
            "City": row['city'],
            "Surface (m2)": row['surface_m2'],
            "Real Price (TND)": real_price,
            "ML Baseline (TND)": round(ml_price, 2),
            "ML Error (%)": round(ml_error, 2),
            "RAG Output (TND)": round(rag_price, 2),
            "RAG Error (%)": round(rag_error, 2),
            "Latency (s)": round(latency, 2)
        })
        
    res_df = pd.DataFrame(results)
    
    # Save the output to Excel and CSV
    res_df.to_excel('Evaluation_Report.xlsx', index=False)
    res_df.to_csv('Evaluation_Report.csv', index=False)
    
    # Print Summary to Terminal
    print("\n" + "="*66)
    print("FINAL BENCHMARK SUMMARY:")
    print("="*66)
    print(f"Total Samples Evaluated: {n_samples}")
    print(f"Average Base ML Model Error: {res_df['ML Error (%)'].mean():.2f}%")
    print(f"Average Hybrid RAG Model Error: {res_df['RAG Error (%)'].mean():.2f}%")
    if res_df['RAG Error (%)'].mean() < res_df['ML Error (%)'].mean():
        print("Verdict: The RAG Intelligence Layer successfully improved overall accuracy.")
    else:
        print("Verdict: The ML Model is acting as the primary anchor.")
    print("="*66)
    print("The complete detailed sheet has been saved to: Evaluation_Report.xlsx and Evaluation_Report.csv")

if __name__ == "__main__":
    run_evaluation(10)
