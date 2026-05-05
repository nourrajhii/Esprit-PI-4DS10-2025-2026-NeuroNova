"""
Villa3D Cloud Stub — port 8056
SD+LoRA model is too large for cloud (3.3GB, needs GPU).
This stub keeps the frontend happy and forwards all 3D work to Tripo API.

Supported endpoints (matching the full local villa3d service):
  GET  /health
  POST /generate3d-text    → text-to-3D via Tripo (JSON body)
  POST /convert3d-direct   → image-to-3D via Tripo (form/file)
  POST /convert3d-multiview → image-to-3D via Tripo (form/file)
  POST /generate2d         → unavailable (SD requires GPU)
  POST /convert3d          → same as convert3d-direct (legacy)
  GET  /task/{task_id}     → proxy Tripo task status
  GET  /download/{filename} → serve cached GLB
"""
import os, json, base64, time, urllib.request, urllib.error, tempfile
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Villa3D Cloud Stub")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

TRIPO_API_KEY = os.getenv("TRIPO_API_KEY", "")
TRIPO_BASE    = "https://api.tripo3d.ai/v2/openapi"

# Temp dir to cache downloaded GLBs
GLB_DIR = Path(tempfile.mkdtemp(prefix="villa3d_glb_"))


# ── Pydantic models ───────────────────────────────────────────────────────────

class TextTo3DRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None
    model_version: Optional[str] = "v3.1-20260211"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tripo_post(path: str, payload: dict, timeout: int = 30) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{TRIPO_BASE}{path}", data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TRIPO_API_KEY}"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _tripo_get(path: str, timeout: int = 15) -> dict:
    req = urllib.request.Request(
        f"{TRIPO_BASE}{path}",
        headers={"Authorization": f"Bearer {TRIPO_API_KEY}"},
        method="GET"
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _upload_image(img_bytes: bytes) -> str:
    """Upload image to Tripo, return file_token."""
    b64 = base64.b64encode(img_bytes).decode()
    resp = _tripo_post("/upload", {"type": "image/jpeg", "data": b64}, timeout=30)
    return resp["data"]["image_token"]


def _poll_task(task_id: str, max_wait: int = 300) -> dict:
    """Poll Tripo task until success/failure, return task data."""
    start = time.time()
    while time.time() - start < max_wait:
        resp = _tripo_get(f"/task/{task_id}", timeout=15)
        status = resp["data"]["status"]
        if status == "success":
            return resp["data"]
        if status in ("failed", "cancelled"):
            raise HTTPException(
                status_code=502,
                detail=f"Tripo task {status}: {resp['data'].get('error', 'unknown error')}"
            )
        time.sleep(5)
    raise HTTPException(status_code=504, detail="Tripo task timed out after 5 minutes")


def _download_glb(task_data: dict, prefix: str = "villa") -> dict:
    """Download GLB from completed task, cache it, return {url, filename, size_kb}."""
    model_url = task_data.get("result", {}).get("model", {}).get("url")
    if not model_url:
        raise HTTPException(status_code=502, detail="Tripo returned no model URL")

    task_id = task_data["task_id"]
    filename = f"{prefix}_{task_id[:8]}.glb"
    dest = GLB_DIR / filename

    with urllib.request.urlopen(model_url, timeout=60) as r:
        dest.write_bytes(r.read())

    size_kb = dest.stat().st_size // 1024
    return {"url": f"/download/{filename}", "filename": filename, "size_kb": size_kb}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": "cloud-stub",
        "sd_available": False,
        "sd_status": "error",        # stops frontend from polling for SD
        "tripo_available": bool(TRIPO_API_KEY),
        "note": "SD disabled in cloud. Text→3D and Photo→3D work via Tripo API."
    }


@app.get("/download/{filename}")
def serve_glb(filename: str):
    """Serve a generated GLB file."""
    path = GLB_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="GLB not found (may have expired)")
    return FileResponse(str(path), media_type="model/gltf-binary", filename=filename)


@app.post("/generate3d-text")
async def generate3d_text(body: TextTo3DRequest):
    """Text → 3D via Tripo text_to_model (JSON body)."""
    if not TRIPO_API_KEY:
        raise HTTPException(status_code=503, detail="TRIPO_API_KEY not configured")
    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is required")

    payload: dict = {"type": "text_to_model", "prompt": body.prompt.strip()}
    if body.model_version:
        payload["model_version"] = body.model_version

    resp = _tripo_post("/task", payload, timeout=30)
    task_id = resp["data"]["task_id"]
    task_data = _poll_task(task_id, max_wait=300)
    return _download_glb(task_data, prefix="text3d")


@app.post("/convert3d-direct")
async def convert3d_direct(file: UploadFile = File(...)):
    """Image → 3D via Tripo image_to_model."""
    if not TRIPO_API_KEY:
        raise HTTPException(status_code=503, detail="TRIPO_API_KEY not configured")

    img_bytes = await file.read()
    file_token = _upload_image(img_bytes)

    resp = _tripo_post("/task", {
        "type": "image_to_model",
        "file": {"type": "jpg", "file_token": file_token}
    }, timeout=30)
    task_id = resp["data"]["task_id"]
    task_data = _poll_task(task_id, max_wait=300)
    return _download_glb(task_data, prefix="direct3d")


@app.post("/convert3d-multiview")
async def convert3d_multiview(file: UploadFile = File(...)):
    """Image → 3D HD via Tripo (multiview consistency)."""
    if not TRIPO_API_KEY:
        raise HTTPException(status_code=503, detail="TRIPO_API_KEY not configured")

    img_bytes = await file.read()
    file_token = _upload_image(img_bytes)

    resp = _tripo_post("/task", {
        "type": "image_to_model",
        "file": {"type": "jpg", "file_token": file_token},
        "multiview_consistency": True,
    }, timeout=30)
    task_id = resp["data"]["task_id"]
    task_data = _poll_task(task_id, max_wait=360)
    return _download_glb(task_data, prefix="mv3d")


@app.post("/convert3d")
async def convert3d_legacy(file: UploadFile = File(...)):
    """Legacy endpoint — delegates to convert3d-direct."""
    return await convert3d_direct(file)


@app.post("/generate2d")
async def generate2d(file: UploadFile = File(...), prompt: Optional[str] = Form(None)):
    """SD+LoRA generation unavailable in cloud (requires GPU)."""
    raise HTTPException(
        status_code=503,
        detail=(
            "Stable Diffusion requires a GPU and is only available in the local deployment. "
            "Use 'Texte → 3D' or 'Photo → 3D' modes instead."
        )
    )


@app.get("/task/{task_id}")
def get_task(task_id: str):
    """Proxy task status from Tripo API."""
    if not TRIPO_API_KEY:
        raise HTTPException(status_code=503, detail="TRIPO_API_KEY not configured")
    return _tripo_get(f"/task/{task_id}", timeout=15)
