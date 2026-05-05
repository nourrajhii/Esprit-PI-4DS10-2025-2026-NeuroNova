"""
Villa3D Cloud Stub — port 8056
SD+LoRA model is too large for cloud (3.3GB, needs GPU).
This stub keeps the frontend happy and forwards image→3D to Tripo API directly.
"""
import os, json, base64, urllib.request, urllib.error
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Villa3D Cloud Stub")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

TRIPO_API_KEY = os.getenv("TRIPO_API_KEY", "")
TRIPO_BASE    = "https://api.tripo3d.ai/v2/openapi"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": "cloud-stub",
        "sd_available": False,
        "tripo_available": bool(TRIPO_API_KEY),
        "note": "SD generation disabled in cloud. Upload an image to /convert3d for Tripo3D."
    }


@app.post("/generate")
async def generate(prompt: str = "modern villa"):
    """SD generation not available in cloud — returns instructions."""
    return {
        "status": "unavailable",
        "message": "Image generation via Stable Diffusion requires a GPU and is only available locally.",
        "alternative": "Use /convert3d with your own image to create a 3D model via Tripo API.",
        "local_url": "http://localhost:8056/generate"
    }


@app.post("/convert3d")
async def convert3d(file: UploadFile = File(...)):
    """Accept an uploaded image and send directly to Tripo3D API."""
    if not TRIPO_API_KEY:
        raise HTTPException(status_code=503, detail="TRIPO_API_KEY not configured")

    img_bytes = await file.read()
    b64 = base64.b64encode(img_bytes).decode()

    # Upload image to Tripo
    upload_payload = json.dumps({
        "type": "image/jpeg",
        "data": b64
    }).encode()
    req = urllib.request.Request(
        f"{TRIPO_BASE}/upload",
        data=upload_payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {TRIPO_API_KEY}"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        upload_data = json.loads(r.read())
    image_token = upload_data["data"]["image_token"]

    # Create 3D task
    task_payload = json.dumps({
        "type": "image_to_model",
        "file": {"type": "jpg", "file_token": image_token}
    }).encode()
    req2 = urllib.request.Request(
        f"{TRIPO_BASE}/task",
        data=task_payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {TRIPO_API_KEY}"},
        method="POST"
    )
    with urllib.request.urlopen(req2, timeout=30) as r:
        task_data = json.loads(r.read())
    task_id = task_data["data"]["task_id"]

    return {"status": "processing", "task_id": task_id,
            "poll_url": f"{TRIPO_BASE}/task/{task_id}",
            "message": "3D model is being generated. Poll the task_id for results."}


@app.get("/task/{task_id}")
def get_task(task_id: str):
    """Proxy task status from Tripo API."""
    if not TRIPO_API_KEY:
        raise HTTPException(status_code=503, detail="TRIPO_API_KEY not configured")
    req = urllib.request.Request(
        f"{TRIPO_BASE}/task/{task_id}",
        headers={"Authorization": f"Bearer {TRIPO_API_KEY}"},
        method="GET"
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())
