import os
import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Set visualization style
plt.style.use('ggplot')
sns.set_theme(style="whitegrid")

PIPELINE_DIR = "pipeline"
MODEL_PATH = "models/price_model.joblib"
OUTPUT_DIR = "presentation_charts"

def generate_academic_graphs():
    print("==================================================================")
    print("  EstateMind AI: Generating Academic Model Evaluation Suite")
    print("==================================================================")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. Load the Test Data and the Trained Model
    print("[1/4] Loading Full Test Dataset and ML Model...")
    X_test = pd.read_csv(f"{PIPELINE_DIR}/X_test.csv")
    y_test_log = pd.read_csv(f"{PIPELINE_DIR}/y_test.csv").squeeze()
    
    model = joblib.load(MODEL_PATH)
    
    # Predict in log space, then convert to original TND Space
    y_pred_log = model.predict(X_test)
    y_pred_tnd = np.expm1(y_pred_log)
    y_true_tnd = np.expm1(y_test_log)
    
    # Calculate Academic Metrics
    mae = mean_absolute_error(y_true_tnd, y_pred_tnd)
    r2 = r2_score(y_true_tnd, y_pred_tnd)
    mape = np.mean(np.abs((y_true_tnd - y_pred_tnd) / y_true_tnd)) * 100
    
    print(f"Metrics over all {len(X_test)} Test Samples:")
    print(f" - R^2 Score   : {r2:.4f}")
    print(f" - Mean Abs Err: {mae:,.0f} TND")
    print(f" - Mean Abs %  : {mape:.2f} %")
    
    # -------------------------------------------------------------------------
    # Chart 1: Actual vs. Predicted (The "Ideal Fit" Line)
    # -------------------------------------------------------------------------
    print("[2/4] Generating Actual vs Predicted Plot...")
    plt.figure(figsize=(10, 6))
    plt.scatter(y_true_tnd, y_pred_tnd, alpha=0.6, color='#4f46e5', edgecolors='w', s=80)
    
    # Plot ideal line (y = x)
    max_val = max(y_true_tnd.max(), y_pred_tnd.max())
    plt.plot([0, max_val], [0, max_val], '--', color='red', linewidth=2, label='Ideal Perfect Model')
    
    plt.title('Baseline ML: Actual vs. Predicted Property Prices (TND)', fontsize=14, pad=15)
    plt.xlabel('Actual Market Price (TND)', fontsize=12)
    plt.ylabel('Gradient Boosting Prediction (TND)', fontsize=12)
    plt.ticklabel_format(style='plain', axis='both')
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/1_Actual_vs_Predicted.png", dpi=300)
    plt.close()
    
    # -------------------------------------------------------------------------
    # Chart 2: Residual Analysis Plot
    # -------------------------------------------------------------------------
    print("[3/4] Generating Residuals Analysis Plot (Homoscedasticity Check)...")
    residuals = y_true_tnd - y_pred_tnd
    plt.figure(figsize=(10, 6))
    plt.scatter(y_pred_tnd, residuals, alpha=0.5, color='#06b6d4', s=60)
    plt.axhline(0, color='red', linestyle='--', linewidth=2)
    
    plt.title('Residual Analysis Plot (Prediction Errors)', fontsize=14, pad=15)
    plt.xlabel('Predicted Property Price (TND)', fontsize=12)
    plt.ylabel('Residuals (Actual - Predicted) TND', fontsize=12)
    plt.ticklabel_format(style='plain', axis='both')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/2_Residual_Distribution.png", dpi=300)
    plt.close()

    # -------------------------------------------------------------------------
    # Chart 3: Feature Importance Bar Chart
    # -------------------------------------------------------------------------
    print("[4/4] Generating Feature Importance (What drives the Tunisian Market)...")
    importances = model.feature_importances_
    features = list(X_test.columns)
    
    # Create DataFrame for plotting
    fi_df = pd.DataFrame({'Feature': features, 'Importance': importances})
    fi_df = fi_df.sort_values(by='Importance', ascending=True)
    
    plt.figure(figsize=(10, 8))
    plt.barh(fi_df['Feature'], fi_df['Importance'], color='#a855f7')
    plt.title('Model Interpretability: Key Features Driving Real Estate Prices', fontsize=14, pad=15)
    plt.xlabel('Relative Importance (Gini Importance)', fontsize=12)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/3_Feature_Importance.png", dpi=300)
    plt.close()

    print("==================================================================")
    print("✅ SUCCESS! Academic Visualizations saved in 'presentation_charts/'")
    print("   ↳ 1_Actual_vs_Predicted.png - Shows correlation against Y=X")
    print("   ↳ 2_Residual_Distribution.png - Proves homoscedasticity/error randomness")
    print("   ↳ 3_Feature_Importance.png - Explainable AI (What drives price)")
    print("==================================================================")

if __name__ == "__main__":
    generate_academic_graphs()
