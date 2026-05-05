FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 5 -r requirements.txt
COPY . .
EXPOSE 8003
# Run core legal app (port 8011 internal) AND invoke adapter (port 8003)
CMD ["sh", "-c", "uvicorn app.main:app --host 127.0.0.1 --port 8011 & sleep 5 && uvicorn invoke_adapter:app --host 0.0.0.0 --port 8003"]
