FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn python-multipart httpx
COPY main.py .
EXPOSE 8056
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8056"]
