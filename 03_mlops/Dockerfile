FROM python:3.11-slim

WORKDIR /app

# Dépendances système pour Prophet / statsmodels
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Requirements Python
COPY 04_deployment/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code de l'application
COPY 04_deployment/backend/ ./backend/

# Modèles (best_model.json + pkl/keras)
COPY 02_modeling/outputs/models/ ./models/
COPY 02_modeling/outputs/best_model.json ./best_model.json

EXPOSE 8000

ENV PYTHONPATH=/app
ENV MODEL_DIR=/app/models
ENV BEST_MODEL_JSON=/app/best_model.json

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
