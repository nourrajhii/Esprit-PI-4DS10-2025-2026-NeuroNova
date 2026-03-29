# EstateMind: Tunisian Real Estate Data Pipeline & AI Automation

EstateMind is a comprehensive, high-performance data harvesting and artificial intelligence engine tailored specifically for the Tunisian real estate ecosystem. It automates the discovery, extraction, cleaning, and modeling of real estate data, providing predictive analytics and generative design capabilities.

## Architecture Overview

The system operates through a structured, multi-stage pipeline designed for data completeness, quality assurance, and automated machine learning.

### 1. Data Collection (Discovery and Scraping)
**Primary Logic:** `main.py`, `discovery/explorer.py`, `scrapers/`
The scraping engine recursively mapped the Tunisian real estate ecosystem:
- **Deep Discovery:** Utilizes search engine APIs (e.g., SerpAPI) to paginate through and locate regional real estate agencies based on specific queries.
- **Exhaustive Mapping:** Scans sitemaps and DNS records to find niche or unlisted agencies.
- **Specialized & Generic Extraction:** Employs custom scraping logic for major platforms and a heuristic fallback system (using BeautifulSoup4) for generic websites.
- **Media Harvesting:** Asynchronously downloads and organizes property images without blocking the main scraping thread.

### 2. Data Cleaning and Filtration
**Primary Logic:** `processing/cleaner.py`
Raw data is synchronized in real-time to MongoDB Atlas. Stage 1 of the AI pipeline prepares this data:
- **Geographical Enforcement:** Implements strict keyword whitelists and blacklists to guarantee the dataset contains exclusively Tunisian properties.
- **Quality Assurance:** Identifies and securely drops corrupted data, outlier prices, and erroneous property parameters.
- **Text Normalization:** Standardizes property titles, cities, and formatting for Natural Language Processing compatibility.

### 3. Feature Engineering and Predictive Modeling
**Primary Logic:** `processing/feature_engineering.py`, `processing/model_trainer.py`
The cleaned data is transformed into a predictive asset:
- **Feature Engineering:** Derives metrics such as price per square meter, categorizes cities into valuation tiers, and applies log transformations for skewed variables.
- **Model Training:** Utilizes a Gradient Boosting Regressor to predict property prices based on the engineered features. The model automatically retrains during each major pipeline cycle, organically increasing its accuracy as the database grows.
- **Performance Auditing:** Maintains a continuous log of model accuracy (R-squared, MAPE) to track performance metrics over time.

### 4. Generative AI Property Visualization
**Primary Logic:** `processing/terrain_generator.py`, `generate_villa.py`
Leverages architectural computer vision to visualize real estate investments.
- **Image-to-Image Generation:** Utilizes Hugging Face's Stable Diffusion InstructPix2Pix model to transform images of empty land or existing structures into generated 3D conceptual architectural renders.
- **Dynamic Prompting:** Supports customizable text prompts allowing the automatic rendering of specific structures such as modern villas, apartment complexes, or minimalist houses based on the terrain.

---

## Command Reference

Below are the primary commands required to operate the various modules of the application.

### The Main Collection Engine
Initiates a complete cycle of discovery, scraping, media downloading, and automatic AI model retraining.
```powershell
python main.py
```

### Manual AI Pipeline Execution
Processes existing MongoDB data (cleaning, feature engineering, and model training) without initiating a new web scraping cycle.
```powershell
python run_pipeline.py
```

### Price Prediction Testing
Tests the currently trained predictive model by estimating the price of a simulated property.
```powershell
python predict_example.py
```

### Generative AI Design
Transforms an image of an empty terrain into a customized 3D architectural render.
```powershell
python generate_villa.py "path/to/image.jpg" --type "modern luxury villa" --style "realistic 8k render"
```

### Database Diagnostics
Outputs the current total count of listings successfully stored in the local environment database.
```powershell
python get_count.py
```

## Directory Structure
- `pipeline/`: Standardized, AI-ready CSV files utilized for training.
- `models/`: The compiled machine learning models (`.joblib`) and historical performance tracking.
- `downloads/`: Automatically collected media, organized into property images and AI-generated renders.
