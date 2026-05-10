FROM python:3.11-slim

WORKDIR /app

# System deps for Pillow, torch CPU, and trimesh
# NOTE: libgl1-mesa-glx was removed in Debian Trixie (Debian 13).
# Use libgl1 (the new umbrella package) — it pulls in the same OpenGL runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl libglib2.0-0 libsm6 libxext6 libxrender-dev libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install CPU-only torch first (smaller image — GPU users override at runtime)
RUN pip install --no-cache-dir torch==2.2.2+cpu torchvision==0.17.2+cpu \
      --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-create output directory
RUN mkdir -p /app/output

EXPOSE 8056

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8056/health || exit 1

CMD ["python", "api_service.py"]
