FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc g++ curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 5 -r requirements.txt
COPY . .
EXPOSE 8002
# Run both core devis app (port 8009 internal) AND invoke adapter (port 8002) as processes
CMD ["sh", "-c", "uvicorn api:app --host 127.0.0.1 --port 8009 & sleep 5 && uvicorn invoke_adapter:app --host 0.0.0.0 --port 8002"]
