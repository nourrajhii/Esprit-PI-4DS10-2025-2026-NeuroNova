"""
EstateMind -- Villa 3D API Service (port 8056)
Step 1: terrain image --> villa 2D via SD v1.5 + LoRA fine-tune
Step 2: villa 2D --> 3D GLB via Tripo3D v2 API
         Modes: image_to_model | text_to_model | multiview pipeline

Start: python api_service.py
"""

import base64
import io
import os
import threading
import requests
import numpy as np
from datetime import datetime
from pydantic import BaseModel

import torch
from diffusers import StableDiffusionImg2ImgPipeline
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image, ImageEnhance, ImageFilter

from mesh_generation_agent import MeshGenerationAgent

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
LORA_DIR   = os.path.join(BASE_DIR, "lora-villa")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

_mesh_agent = MeshGenerationAgent()

# ── SD + LoRA pipeline (loaded in background thread) ─────────────────────────
_pipe        = None
_pipe_status = "loading"   # "loading" | "ready" | "error"
_pipe_error  = ""

# Prompt for clean isolated building — Tripo3D image_to_model requires a single
# object on a plain background. Any sky/terrain/plants causes degenerate 3D output.
VILLA_PROMPT = (
    "luxury Mediterranean villa, isolated building, pure white background, "
    "centered product-shot view, full exterior, no ground no sky no plants, "
    "architectural 3D render style, sharp edges, bright uniform lighting, "
    "white stucco facade, terracotta roof tiles, photorealistic"
)
VILLA_NEGATIVE = (
    "cartoon, anime, sketch, low quality, blurry, interior, people, text, "
    "watermark, ugly, deformed, out of frame, landscape, garden, pool, street, "
    "cars, trees, sky, ground, grass, shadow, gradient, multiple buildings, "
    "busy background, dark, gloomy, birds-eye, aerial"
)


def _load_pipeline():
    global _pipe, _pipe_status, _pipe_error
    try:
        print("[SD] Chargement du modele runwayml/stable-diffusion-v1-5 ...")
        pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float32,
            safety_checker=None,
            requires_safety_checker=False,
        )

        lora_weights = os.path.join(LORA_DIR, "pytorch_lora_weights.safetensors")
        if os.path.exists(lora_weights):
            print(f"[LoRA] Chargement des poids LoRA villa depuis {lora_weights}")
            pipe.load_lora_weights(LORA_DIR)
            print("[LoRA] Poids LoRA charges avec succes")
        else:
            print(f"[WARNING] Fichier LoRA introuvable : {lora_weights}")

        pipe = pipe.to("cpu")
        _pipe = pipe
        _pipe_status = "ready"
        print("[SD] Pipeline SD + LoRA pret !")
    except Exception as e:
        _pipe_error  = str(e)
        _pipe_status = "error"
        print(f"[ERREUR] Chargement pipeline echoue : {e}")


# Charge en arriere-plan pour que le serveur demarre immediatement
_loader_thread = threading.Thread(target=_load_pipeline, daemon=True)
_loader_thread.start()

# ── State ─────────────────────────────────────────────────────────────────────
_generated_image = None

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="EstateMind Villa 3D API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _white_background(img: Image.Image, threshold: int = 230) -> Image.Image:
    """
    Replace near-white pixels (>threshold on all channels) with pure white.
    Helps Tripo3D isolate the building cleanly before remove_background.
    """
    arr = np.array(img.convert("RGB"))
    mask = (arr[:, :, 0] > threshold) & (arr[:, :, 1] > threshold) & (arr[:, :, 2] > threshold)
    arr[mask] = [255, 255, 255]
    return Image.fromarray(arr)


def _img_to_b64(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status":       "ok",
        "service":      "villa3d",
        "provider":     "tripo3d.ai",
        "sd_status":    _pipe_status,     # "loading" | "ready" | "error"
        "sd_available": _pipe is not None,
        "sd_error":     _pipe_error or None,
    }


# ── Step 1: terrain --> villa 2D via SD + LoRA ────────────────────────────────
@app.post("/generate2d")
async def generate_2d(file: UploadFile = File(...), prompt: str = Form(None)):
    """
    Prend une image de terrain, genere une villa dessus via SD v1.5 + LoRA villa.
    Si le pipeline n'est pas encore pret, retourne une erreur claire.
    """
    global _generated_image

    # Lire et decoder l'image d'entree
    contents = await file.read()
    try:
        input_image = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image invalide : {e}")

    # Verifier que le pipeline est pret
    if _pipe_status == "loading":
        raise HTTPException(
            status_code=503,
            detail=(
                "Le modele Stable Diffusion est encore en cours de chargement "
                "(peut prendre 2-5 min au premier demarrage). "
                "Verifiez /health et reessayez dans quelques instants."
            ),
        )

    if _pipe_status == "error" or _pipe is None:
        raise HTTPException(
            status_code=500,
            detail=f"Echec chargement du modele SD+LoRA : {_pipe_error}",
        )

    # Use provided prompt if non-empty, otherwise fall back to default
    active_prompt = prompt.strip() if prompt and prompt.strip() else VILLA_PROMPT

    # Generation via Stable Diffusion + LoRA
    try:
        inp = input_image.resize((512, 512))

        result = _pipe(
            prompt=active_prompt,
            negative_prompt=VILLA_NEGATIVE,
            image=inp,
            strength=0.82,           # high strength → departs from terrain, gets clean isolated building
            num_inference_steps=50,
            guidance_scale=9.5,
        ).images[0]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation SD echouee : {e}")

    # White-out near-white background pixels so Tripo3D remove_background works cleanly
    result = _white_background(result)

    _generated_image = result
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Save a high-res copy for Tripo3D (upscaled to 1024, background already cleaned)
    result_hd = result.resize((1024, 1024), Image.LANCZOS)
    result_hd.save(os.path.join(OUTPUT_DIR, f"villa_{ts}.png"), "PNG")

    return {
        "image":  _img_to_b64(result),
        "status": "Villa 2D generee (SD v1.5 + LoRA villa)",
        "mode":   "SD+LoRA",
    }


def _glb_response(glb_path: str, glb_filename: str, mode: str):
    size_kb = os.path.getsize(glb_path) // 1024
    return {
        "url":      f"/download/{glb_filename}",
        "filename": glb_filename,
        "size_kb":  size_kb,
        "status":   f"Modele 3D pret — {glb_filename} ({size_kb} KB)",
        "mode":     mode,
    }


# ── Step 2: villa 2D --> 3D GLB via Tripo3D ──────────────────────────────────
@app.post("/convert3d")
async def convert_3d():
    """Convertit la derniere image SD generee en modele 3D GLB via Tripo3D."""
    global _generated_image

    if _generated_image is None:
        raise HTTPException(status_code=400, detail="Generez d'abord la villa 2D")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_path    = os.path.join(OUTPUT_DIR, f"temp_{ts}.png")
    glb_filename = f"villa_3d_{ts}.glb"
    glb_path     = os.path.join(OUTPUT_DIR, glb_filename)

    # Upscale to 1024x1024, centre on white canvas (pure white → clean Tripo3D isolation)
    hd = _white_background(_generated_image.copy())
    hd.thumbnail((1024, 1024), Image.LANCZOS)
    canvas = Image.new("RGB", (1024, 1024), (255, 255, 255))
    canvas.paste(hd, ((1024 - hd.width) // 2, (1024 - hd.height) // 2))
    canvas.save(temp_path, "PNG")

    try:
        _mesh_agent.generate(temp_path, glb_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Echec generation 3D : {exc}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return _glb_response(glb_path, glb_filename, "tripo3d")


# ── Direct image → 3D (no SD step) ───────────────────────────────────────────
@app.post("/convert3d-direct")
async def convert_3d_direct(file: UploadFile = File(...)):
    """Upload any image directly to Tripo3D v3.1 — skips the SD step."""
    contents = await file.read()
    try:
        img = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image invalide : {e}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    img_path     = os.path.join(OUTPUT_DIR, f"direct_{ts}.png")
    glb_filename = f"villa_3d_{ts}.glb"
    glb_path     = os.path.join(OUTPUT_DIR, glb_filename)

    # Keep aspect ratio, pad to square at 1024 for best Tripo3D results
    img.thumbnail((1024, 1024), Image.LANCZOS)
    canvas = Image.new("RGB", (1024, 1024), (255, 255, 255))
    canvas.paste(img, ((1024 - img.width) // 2, (1024 - img.height) // 2))
    canvas.save(img_path, "PNG")

    try:
        _mesh_agent.generate(img_path, glb_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Echec generation 3D : {exc}")
    finally:
        if os.path.exists(img_path):
            os.remove(img_path)

    return _glb_response(glb_path, glb_filename, "tripo3d-direct")


# ── Direct image → 3D with multiview pipeline ────────────────────────────────
@app.post("/convert3d-multiview")
async def convert_3d_multiview(file: UploadFile = File(...)):
    """
    Best-quality pipeline: upload image → generate 4 views → multiview_to_model.
    Takes ~3-5 minutes but produces superior geometry.
    """
    contents = await file.read()
    try:
        img = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image invalide : {e}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    img_path     = os.path.join(OUTPUT_DIR, f"mv_{ts}.png")
    glb_filename = f"villa_3d_{ts}.glb"
    glb_path     = os.path.join(OUTPUT_DIR, glb_filename)

    img.thumbnail((1024, 1024), Image.LANCZOS)
    canvas = Image.new("RGB", (1024, 1024), (255, 255, 255))
    canvas.paste(img, ((1024 - img.width) // 2, (1024 - img.height) // 2))
    canvas.save(img_path, "PNG")

    try:
        _mesh_agent.generate(img_path, glb_path, use_multiview=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Echec multiview 3D : {exc}")
    finally:
        if os.path.exists(img_path):
            os.remove(img_path)

    return _glb_response(glb_path, glb_filename, "tripo3d-multiview")


# ── Text → 3D via text_to_model ──────────────────────────────────────────────
class TextTo3DRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    model_version: str = ""


@app.post("/generate3d-text")
async def generate_3d_text(body: TextTo3DRequest):
    """
    Generate a 3D model directly from a text description via Tripo3D text_to_model.
    No image needed — just describe the building/object.
    """
    if not body.prompt or not body.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt est requis")

    prompt = body.prompt.strip()[:1024]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    glb_filename = f"villa_3d_{ts}.glb"
    glb_path     = os.path.join(OUTPUT_DIR, glb_filename)

    try:
        _mesh_agent.generate_from_text(
            prompt=prompt,
            output_path=glb_path,
            negative_prompt=body.negative_prompt,
            model_version=body.model_version,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Echec text-to-3D : {exc}")

    return _glb_response(glb_path, glb_filename, "tripo3d-text")


# ── Download GLB ──────────────────────────────────────────────────────────────
@app.get("/download/{filename}")
def download_glb(filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path) or not filename.endswith(".glb"):
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    # Serve inline (no Content-Disposition: attachment) so the browser fetch() can read it
    # The frontend downloads via a blob URL, not a direct anchor download
    return FileResponse(path, media_type="model/gltf-binary")


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  EstateMind Villa 3D API  --  port 8056")
    print("  SD v1.5 + LoRA villa  -->  Triverse.ai 3D")
    print("  Chargement du modele en cours en arriere-plan...")
    print("  Verifiez http://localhost:8056/health pour le statut")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8056, log_level="info")
