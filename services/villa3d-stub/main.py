"""
Villa3D Cloud Stub — port 8056
Fully async (httpx + asyncio.sleep) — event loop never blocked.

Tripo API structure (confirmed from local service):
  upload:  POST /upload  multipart files={"file": (...)}  → data.image_token
  task:    POST /task    JSON body                        → data.task_id
  poll:    GET  /task/{id}                               → data.output.pbr_model | data.output.model
"""
import os, asyncio, tempfile
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


def _auth() -> dict:
    return {"Authorization": f"Bearer {TRIPO_API_KEY}"}


def _require_key():
    if not TRIPO_API_KEY:
        raise HTTPException(503, detail="TRIPO_API_KEY not configured on server")


# ── Tripo helpers ─────────────────────────────────────────────────────────────

async def _post_task(payload: dict) -> str:
    """Submit a Tripo task, return task_id."""
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{TRIPO_BASE}/task", json=payload, headers=_auth())
            if r.status_code == 401:
                raise HTTPException(401, "Tripo API key invalid or expired")
            if r.status_code in (402, 403):
                raise HTTPException(402, "Tripo credits exhausted — recharge at platform.tripo3d.ai")
            r.raise_for_status()
            return r.json()["data"]["task_id"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, detail=f"Tripo task submission failed: {e}")


async def _upload_image(img_bytes: bytes, filename: str = "image.jpg") -> str:
    """Upload image to Tripo using multipart form (same as local service), return image_token."""
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                f"{TRIPO_BASE}/upload",
                headers=_auth(),
                files={"file": (filename, img_bytes, "image/jpeg")},
            )
            if r.status_code == 401:
                raise HTTPException(401, "Tripo API key invalid or expired")
            r.raise_for_status()
            token = r.json()["data"].get("image_token")
            if not token:
                raise HTTPException(502, "No image_token in Tripo upload response")
            return token
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, detail=f"Tripo upload failed: {e}")


async def _poll_task(task_id: str, max_wait: int = 300) -> dict:
    """Async-poll Tripo until success. Returns task data dict."""
    waited = 0
    while waited < max_wait:
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get(f"{TRIPO_BASE}/task/{task_id}", headers=_auth())
                r.raise_for_status()
                body = r.json()
                if body.get("code") != 0:
                    await asyncio.sleep(4)
                    waited += 4
                    continue
                data   = body["data"]
                status = data.get("status")
                if status == "success":
                    return data
                if status in ("failed", "cancelled"):
                    reason = data.get("output", {}).get("message", "unknown")
                    raise HTTPException(502, detail=f"Tripo task {status}: {reason}")
        except HTTPException:
            raise
        except Exception:
            pass  # transient network error — keep polling
        await asyncio.sleep(4)
        waited += 4
    raise HTTPException(504, detail="Tripo task timed out after 5 minutes")


async def _finish_glb(task_data: dict, prefix: str = "villa") -> dict:
    """
    Download the GLB from the completed task.
    Tripo response: data.output.pbr_model  (new)  or  data.output.model  (old)
    Both are direct download URLs (strings), not nested objects.
    """
    out       = task_data.get("output", {})
    model_url = out.get("pbr_model") or out.get("model")
    if not model_url:
        raise HTTPException(502, detail=f"Tripo returned no model URL. output keys: {list(out.keys())}")

    task_id  = task_data["task_id"]
    filename = f"{prefix}_{task_id[:8]}.glb"
    dest     = GLB_DIR / filename

    try:
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.get(model_url)
            r.raise_for_status()
            dest.write_bytes(r.content)
    except Exception as e:
        raise HTTPException(502, detail=f"GLB download failed: {e}")

    return {"url": f"/download/{filename}", "filename": filename,
            "size_kb": dest.stat().st_size // 1024}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok", "mode": "cloud-stub",
        "sd_available": False, "sd_status": "error",
        "tripo_available": bool(TRIPO_API_KEY),
        "note": "SD disabled in cloud. Text→3D and Photo→3D work via Tripo API.",
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
    model_version: Optional[str] = "v2.5-20250123"


@app.post("/generate3d-text")
async def generate3d_text(body: TextTo3DBody):
    """Text → 3D via Tripo text_to_model."""
    _require_key()
    if not body.prompt.strip():
        raise HTTPException(400, detail="prompt is required")
    payload = {"type": "text_to_model", "prompt": body.prompt.strip()}
    if body.model_version:
        payload["model_version"] = body.model_version
    task_id   = await _post_task(payload)
    task_data = await _poll_task(task_id, max_wait=300)
    return await _finish_glb(task_data, prefix="text3d")


@app.post("/convert3d-direct")
async def convert3d_direct(file: UploadFile = File(...)):
    """Image → 3D via Tripo image_to_model."""
    _require_key()
    img_bytes = await file.read()
    token     = await _upload_image(img_bytes, file.filename or "image.jpg")
    task_id   = await _post_task({
        "type": "image_to_model",
        "file": {"type": "jpg", "file_token": token},
    })
    task_data = await _poll_task(task_id, max_wait=300)
    return await _finish_glb(task_data, prefix="direct3d")


@app.post("/convert3d-multiview")
async def convert3d_multiview(file: UploadFile = File(...)):
    """Image → 3D HD via Tripo (multiview consistency)."""
    _require_key()
    img_bytes = await file.read()
    token     = await _upload_image(img_bytes, file.filename or "image.jpg")
    task_id   = await _post_task({
        "type": "image_to_model",
        "file": {"type": "jpg", "file_token": token},
        "multiview_consistency": True,
    })
    task_data = await _poll_task(task_id, max_wait=360)
    return await _finish_glb(task_data, prefix="mv3d")


@app.post("/convert3d")
async def convert3d_legacy(file: UploadFile = File(...)):
    return await convert3d_direct(file)


@app.post("/generate2d")
async def generate2d(file: UploadFile = File(...)):
    raise HTTPException(503, detail=(
        "Stable Diffusion requires a GPU — only available in the local deployment. "
        "Use 'Texte → 3D' or 'Photo → 3D' instead."
    ))


@app.get("/task/{task_id}")
async def get_task(task_id: str):
    _require_key()
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{TRIPO_BASE}/task/{task_id}", headers=_auth())
            r.raise_for_status()
            return r.json()
    except Exception as e:
        raise HTTPException(502, detail=f"Tripo error: {e}")
