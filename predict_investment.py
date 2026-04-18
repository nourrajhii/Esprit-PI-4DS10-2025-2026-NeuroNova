import argparse
import pandas as pd

def investment_dashboard(budget):
    print("==================================================================")
    print(f"EstateMind AI: Smart Investment Engine (Budget: {budget:,.0f} TND)")
    print("==================================================================")
    
    try:
        df = pd.read_csv('ai_enhanced_listings.csv')
    except FileNotFoundError:
        print("Error: Please run 'python dso_pipeline.py' first to generate ai_enhanced_listings.csv")
        return
        
    # Filter for valid sales within budget
    affordable = df[(df['inferred_type'] == 'vente') & 
                    (df['price'] <= budget) & 
                    (df['price'] > 50000) & 
                    (df['is_duplicate'] == False)]
                    
    if affordable.empty:
        print("No properties found within this budget. Try increasing your budget.")
        return

    print("\n[🎯 OPTION 1: THE FLIP (Lowest Price per m2)]")
    flip = affordable.sort_values('deal_score_pct', ascending=False).head(1).iloc[0]
    print(f"Title: {flip['title']}")
    print(f"Location: {flip['city']}")
    print(f"Acquisition Cost: {flip['price']:,.0f} TND")
    print(f"Why it's good: It is {flip['deal_score_pct']:.1f}% cheaper than the market average in {flip['city']}!")
    print(f"Market Median: {flip['city_median_m2']:,.0f} TND/m2 | Property: {flip['price_per_m2']:,.0f} TND/m2")

    print("\n[📈 OPTION 2: THE CASH FLOW (Highest ROI %)]")
    # Filter unrealistic ROIs
    roi_options = affordable[affordable['annual_roi_pct'] <= 15]
    if not roi_options.empty:
        cashflow = roi_options.sort_values('annual_roi_pct', ascending=False).head(1).iloc[0]
        print(f"Title: {cashflow['title']}")
        print(f"Location: {cashflow['city']}")
        print(f"Acquisition Cost: {cashflow['price']:,.0f} TND")
        print(f"Expected Monthly Rent: {cashflow['estimated_monthly_rent']:,.0f} TND/mo")
        print(f"Why it's good: It will yield an estimated Annual ROI of {cashflow['annual_roi_pct']:.2f}%.")
    else:
        print("No cash flow properties found within safe parameters.")

    print("\n[🏡 OPTION 3: THE MAXIMUM SURFACE (Biggest Property for Budget)]")
    big = affordable.sort_values('surface_m2', ascending=False).head(1).iloc[0]
    print(f"Title: {big['title']}")
    print(f"Location: {big['city']}")
    print(f"Acquisition Cost: {big['price']:,.0f} TND")
    print(f"Why it's good: You get {big['surface_m2']} m2 for your budget ({(big['price']/big['surface_m2']):,.0f} TND/m2).")
    print("==================================================================")
    print("Powered by EstateMind Predictive Analytics Engine.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Find the best real estate investment for your budget.')
    parser.add_argument('budget', type=float, help='Your maximum budget in TND')
    args = parser.parse_args()
    
    investment_dashboard(args.budget)
