FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc curl && rm -rf /var/lib/apt/lists/*
# Use slim requirements — only what invoke_adapter + rag_backend need
COPY requirements.invoke.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 5 -r requirements.invoke.txt
COPY . .
EXPOSE 8055
CMD ["uvicorn", "invoke_adapter:app", "--host", "0.0.0.0", "--port", "8055"]
