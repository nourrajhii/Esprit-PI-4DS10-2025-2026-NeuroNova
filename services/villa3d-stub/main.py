"""
Villa3D Cloud Stub — port 8056
Fully async (httpx + asyncio.sleep) so CORS preflight is never blocked.

Endpoints:
  GET  /health
  POST /generate3d-text    → text-to-3D via Tripo (JSON body)
  POST /convert3d-direct   → image-to-3D via Tripo (file upload)
  POST /convert3d-multiview → image-to-3D HD via Tripo (file upload)
  POST /convert3d          → alias for convert3d-direct (legacy)
  POST /generate2d         → 503 (SD requires GPU, cloud only)
  GET  /download/{filename} → serve cached GLB
  GET  /task/{task_id}     → proxy Tripo task status
"""
import os, json, base64, asyncio, tempfile
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Villa3D Cloud Stub")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TRIPO_API_KEY = os.getenv("TRIPO_API_KEY", "")
TRIPO_BASE    = "https://api.tripo3d.ai/v2/openapi"
GLB_DIR       = Path(tempfile.mkdtemp(prefix="villa3d_"))

TRIPO_TIMEOUT = httpx.Timeout(30.0, read=60.0)


def _auth() -> dict:
    return {"Authorization": f"Bearer {TRIPO_API_KEY}"}


def _require_key():
    if not TRIPO_API_KEY:
        raise HTTPException(503, detail="TRIPO_API_KEY not configured on server")


# ── Tripo helpers (fully async) ───────────────────────────────────────────────

async def _tripo_post(path: str, payload: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=TRIPO_TIMEOUT) as c:
            r = await c.post(f"{TRIPO_BASE}{path}", json=payload, headers=_auth())
            if r.status_code == 401:
                raise HTTPException(401, detail="Tripo API key is invalid or expired — update TRIPO_API_KEY on the server")
            if r.status_code == 402 or r.status_code == 403:
                raise HTTPException(402, detail="Tripo API credits exhausted — recharge at platform.tripo3d.ai")
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        raise HTTPException(502, detail=f"Tripo API error {e.response.status_code}: {e.response.text[:200]}")
    except Exception as e:
        raise HTTPException(502, detail=f"Tripo connection error: {e}")


async def _tripo_get(path: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=TRIPO_TIMEOUT) as c:
            r = await c.get(f"{TRIPO_BASE}{path}", headers=_auth())
            if r.status_code == 401:
                raise HTTPException(401, detail="Tripo API key is invalid or expired")
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, detail=f"Tripo connection error: {e}")


async def _upload_image(img_bytes: bytes) -> str:
    """Upload raw image bytes to Tripo, return file_token."""
    b64 = base64.b64encode(img_bytes).decode()
    resp = await _tripo_post("/upload", {"type": "image/jpeg", "data": b64})
    return resp["data"]["image_token"]


async def _poll_task(task_id: str, max_wait: int = 300) -> dict:
    """Async-poll Tripo until success or failure (never blocks event loop)."""
    waited = 0
    while waited < max_wait:
        resp = await _tripo_get(f"/task/{task_id}")
        status = resp["data"]["status"]
        if status == "success":
            return resp["data"]
        if status in ("failed", "cancelled"):
            raise HTTPException(502, detail=f"Tripo task {status}: {resp['data'].get('error','')}")
        await asyncio.sleep(4)   # ← asyncio, never blocks event loop
        waited += 4
    raise HTTPException(504, detail="Tripo task timed out after 5 minutes")


async def _finish_glb(task_data: dict, prefix: str = "villa") -> dict:
    """Download GLB from Tripo result, cache it, return {url, filename, size_kb}."""
    model_url = task_data.get("result", {}).get("model", {}).get("url")
    if not model_url:
        raise HTTPException(502, detail="Tripo returned no model URL in result")

    tid      = task_data["task_id"]
    filename = f"{prefix}_{tid[:8]}.glb"
    dest     = GLB_DIR / filename

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as c:
        r = await c.get(model_url)
        r.raise_for_status()
        dest.write_bytes(r.content)

    return {"url": f"/download/{filename}", "filename": filename,
            "size_kb": dest.stat().st_size // 1024}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status":        "ok",
        "mode":          "cloud-stub",
        "sd_available":  False,
        "sd_status":     "error",          # stops frontend SD-loading spinner
        "tripo_available": bool(TRIPO_API_KEY),
        "note":          "SD disabled in cloud. Text→3D and Photo→3D work via Tripo API."
    }


@app.get("/download/{filename}")
def serve_glb(filename: str):
    path = GLB_DIR / filename
    if not path.exists():
        raise HTTPException(404, detail="GLB not found (server restarted or never generated)")
    return FileResponse(str(path), media_type="model/gltf-binary", filename=filename)


class TextTo3DBody(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None
    model_version: Optional[str] = "v3.1-20260211"


@app.post("/generate3d-text")
async def generate3d_text(body: TextTo3DBody):
    """Text → 3D via Tripo text_to_model."""
    _require_key()
    if not body.prompt.strip():
        raise HTTPException(400, detail="prompt is required")

    payload: dict = {"type": "text_to_model", "prompt": body.prompt.strip()}
    if body.model_version:
        payload["model_version"] = body.model_version

    resp      = await _tripo_post("/task", payload)
    task_id   = resp["data"]["task_id"]
    task_data = await _poll_task(task_id, max_wait=300)
    return await _finish_glb(task_data, prefix="text3d")


@app.post("/convert3d-direct")
async def convert3d_direct(file: UploadFile = File(...)):
    """Image → 3D via Tripo image_to_model."""
    _require_key()
    img   = await file.read()
    token = await _upload_image(img)

    resp      = await _tripo_post("/task", {
        "type": "image_to_model",
        "file": {"type": "jpg", "file_token": token}
    })
    task_id   = resp["data"]["task_id"]
    task_data = await _poll_task(task_id, max_wait=300)
    return await _finish_glb(task_data, prefix="direct3d")


@app.post("/convert3d-multiview")
async def convert3d_multiview(file: UploadFile = File(...)):
    """Image → 3D HD via Tripo (multiview consistency flag)."""
    _require_key()
    img   = await file.read()
    token = await _upload_image(img)

    resp      = await _tripo_post("/task", {
        "type": "image_to_model",
        "file": {"type": "jpg", "file_token": token},
        "multiview_consistency": True,
    })
    task_id   = resp["data"]["task_id"]
    task_data = await _poll_task(task_id, max_wait=360)
    return await _finish_glb(task_data, prefix="mv3d")


@app.post("/convert3d")
async def convert3d_legacy(file: UploadFile = File(...)):
    """Legacy endpoint — same as /convert3d-direct."""
    return await convert3d_direct(file)


@app.post("/generate2d")
async def generate2d(file: UploadFile = File(...)):
    """SD generation requires a GPU — not available in cloud."""
    raise HTTPException(503, detail=(
        "Stable Diffusion requires a GPU and is only available in the local deployment. "
        "Use 'Texte → 3D' or 'Photo → 3D' modes instead."
    ))


@app.get("/task/{task_id}")
async def get_task(task_id: str):
    """Proxy Tripo task status."""
    _require_key()
    return await _tripo_get(f"/task/{task_id}")
