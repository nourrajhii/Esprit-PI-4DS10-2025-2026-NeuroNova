"""
MeshGenerationAgent — Tripo3D v2 API  (image_to_model / text_to_model / multiview pipeline)
Fallback: local parametric villa mesh (trimesh).
"""

import logging
import os
import time

import numpy as np
import requests

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
TRIPO_API_KEY       = os.getenv("TRIPO_API_KEY",       "tsk_c0-NGL4YYMvvLJykL54PXKLYIuX4NcIxdu4gnKQovGF")
TRIPO_MODEL_VERSION = os.getenv("TRIPO_MODEL_VERSION", "v2.5-20250123")
TRIPO_POLL_INTERVAL = int(os.getenv("TRIPO_POLL_INTERVAL", "5"))
TRIPO_POLL_TIMEOUT  = int(os.getenv("TRIPO_POLL_TIMEOUT",  "360"))
_BASE               = "https://api.tripo3d.ai/v2/openapi"

# Minimum expected GLB size — anything smaller is a broken/placeholder result
_MIN_GLB_BYTES = 50_000  # 50 KB

# Whether the chosen model supports geometry_quality (v3.0+, not P1)
def _supports_geometry_quality(version: str) -> bool:
    if version.startswith(("P1-", "p1-")):
        return False
    return version.startswith("v3.")

# Base task params — only use params documented for the given model version
def _base_params(version: str) -> dict:
    p: dict = {
        "model_version": version,
        "texture":       True,
        "pbr":           True,
    }
    # texture_quality and geometry_quality are v3.0+ only
    if _supports_geometry_quality(version):
        p["texture_quality"]  = "detailed"
        p["geometry_quality"] = "detailed"
    return p


class MeshGenerationAgent:
    """Converts images or text prompts to textured GLB via Tripo3D API."""

    def __init__(self):
        self._auth         = {"Authorization": f"Bearer {TRIPO_API_KEY}"}
        self._json_headers = {**self._auth, "Content-Type": "application/json"}

    # ── Public: image → GLB ──────────────────────────────────────────────────

    def generate(self, image_path: str, output_path: str, use_multiview: bool = False) -> str:
        """
        image → GLB via Tripo3D.
        If use_multiview=True, runs generate_multiview_image first for best quality.
        Raises on failure so callers get the real Tripo3D error (e.g. insufficient credits).
        """
        if use_multiview:
            return self._multiview_pipeline(image_path, output_path)
        return self._image_pipeline(image_path, output_path)

    # ── Public: text → GLB ──────────────────────────────────────────────────

    def generate_from_text(self, prompt: str, output_path: str,
                           negative_prompt: str = "", model_version: str = "") -> str:
        """text_to_model → GLB."""
        version = model_version or TRIPO_MODEL_VERSION
        task_id = self._create_text_task(prompt, negative_prompt, version)
        model_url = self._poll_task(task_id)
        self._download_glb(model_url, output_path)
        logger.info("Tripo3D text-to-3D GLB saved to %s", output_path)
        return output_path

    # ── Single-image pipeline ─────────────────────────────────────────────────

    def _image_pipeline(self, image_path: str, output_path: str) -> str:
        image_token = self._upload_image(image_path)
        task_id     = self._create_image_task(image_token)
        model_url   = self._poll_task(task_id)
        self._download_glb(model_url, output_path)
        logger.info("Tripo3D image GLB saved to %s", output_path)
        return output_path

    # ── Multiview pipeline ────────────────────────────────────────────────────

    def _multiview_pipeline(self, image_path: str, output_path: str) -> str:
        """generate_multiview_image → multiview_to_model → GLB."""
        image_token = self._upload_image(image_path)

        # Step 1: generate 4 consistent views
        logger.info("Tripo3D: generating multiview images…")
        mv_task_id = self._create_multiview_gen_task(image_token)
        self._poll_task(mv_task_id)   # wait for views to be ready

        # Step 2: multiview → model using the same task_id as original_task_id
        logger.info("Tripo3D: running multiview_to_model…")
        model_task_id = self._create_multiview_model_task(mv_task_id)
        model_url     = self._poll_task(model_task_id)
        self._download_glb(model_url, output_path)
        logger.info("Tripo3D multiview GLB saved to %s", output_path)
        return output_path

    # ── Task creation ─────────────────────────────────────────────────────────

    def _create_image_task(self, image_token: str) -> str:
        payload = {
            "type":                 "image_to_model",
            "file":                 {"type": "png", "file_token": image_token},
            "enable_image_autofix": True,
            "remove_background":    True,
            **_base_params(TRIPO_MODEL_VERSION),
        }
        return self._submit_task(payload, "image_to_model")

    def _create_text_task(self, prompt: str, negative_prompt: str, version: str) -> str:
        payload = {
            "type":   "text_to_model",
            "prompt": prompt[:1024],
            **_base_params(version),
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt[:255]
        return self._submit_task(payload, "text_to_model")

    def _create_multiview_gen_task(self, image_token: str) -> str:
        payload = {
            "type": "generate_multiview_image",
            "file": {"type": "png", "file_token": image_token},
        }
        return self._submit_task(payload, "generate_multiview_image")

    def _create_multiview_model_task(self, original_task_id: str) -> str:
        payload = {
            "type":             "multiview_to_model",
            "original_task_id": original_task_id,
            **_base_params(TRIPO_MODEL_VERSION),
        }
        return self._submit_task(payload, "multiview_to_model")

    def _submit_task(self, payload: dict, step: str) -> str:
        r = requests.post(
            f"{_BASE}/task",
            headers=self._json_headers,
            json=payload,
            timeout=30,
        )
        self._check_response(r, step)
        task_id = r.json()["data"].get("task_id")
        if not task_id:
            raise ValueError(f"task_id missing in {step} response: {r.text[:200]}")
        logger.info("Tripo3D %s task submitted: %s", step, task_id)
        return task_id

    # ── Upload ────────────────────────────────────────────────────────────────

    def _upload_image(self, image_path: str) -> str:
        ext = os.path.splitext(image_path)[1].lstrip(".").lower() or "png"
        mime = f"image/{ext}"
        with open(image_path, "rb") as fh:
            r = requests.post(
                f"{_BASE}/upload",
                headers=self._auth,
                files={"file": (os.path.basename(image_path), fh, mime)},
                timeout=60,
            )
        self._check_response(r, "upload")
        token = r.json()["data"].get("image_token")
        if not token:
            raise ValueError(f"image_token missing in upload response: {r.text[:200]}")
        logger.info("Tripo3D upload OK — token: %s…", token[:20])
        return token

    # ── Polling ───────────────────────────────────────────────────────────────

    def _poll_task(self, task_id: str) -> str:
        """Poll until success; returns model download URL."""
        deadline = time.time() + TRIPO_POLL_TIMEOUT
        while time.time() < deadline:
            r = requests.get(
                f"{_BASE}/task/{task_id}",
                headers=self._auth,
                timeout=30,
            )
            if r.status_code != 200:
                time.sleep(TRIPO_POLL_INTERVAL)
                continue
            body = r.json()
            if body.get("code") != 0:
                time.sleep(TRIPO_POLL_INTERVAL)
                continue
            data     = body["data"]
            status   = data.get("status")
            progress = data.get("progress", 0)
            logger.debug("task %s — status=%s  progress=%s%%", task_id, status, progress)

            if status == "success":
                out = data.get("output", {})
                # API changed: field is now "pbr_model"; fall back to "model" for older versions
                url = out.get("pbr_model") or out.get("model")
                if not url:
                    raise ValueError(f"model URL missing in task output: {list(out.keys())}")
                return url
            if status == "failed":
                reason = data.get("output", {}).get("message", "unknown error")
                raise RuntimeError(f"Tripo3D task {task_id} failed: {reason}")

            time.sleep(TRIPO_POLL_INTERVAL)

        raise TimeoutError(f"Tripo3D task {task_id} timed out after {TRIPO_POLL_TIMEOUT}s")

    # ── Download ──────────────────────────────────────────────────────────────

    def _download_glb(self, model_url: str, output_path: str) -> None:
        r = requests.get(model_url, stream=True, timeout=120)
        if r.status_code != 200:
            raise RuntimeError(f"GLB download failed — HTTP {r.status_code}")
        with open(output_path, "wb") as fh:
            for chunk in r.iter_content(8192):
                fh.write(chunk)
        size = os.path.getsize(output_path)
        logger.info("GLB downloaded: %d bytes → %s", size, output_path)
        if size < _MIN_GLB_BYTES:
            os.remove(output_path)
            raise RuntimeError(
                f"Tripo3D returned a degenerate GLB ({size} bytes < {_MIN_GLB_BYTES} expected). "
                "This usually means: (1) insufficient API credits, (2) the image had no isolatable "
                "object after background removal, or (3) a model-version incompatibility. "
                f"Check your Tripo3D dashboard at https://platform.tripo3d.ai"
            )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _check_response(r: requests.Response, step: str) -> None:
        if r.status_code != 200:
            raise RuntimeError(f"Tripo3D {step} HTTP {r.status_code}: {r.text[:300]}")
        body = r.json()
        if body.get("code") != 0:
            code = body.get("code", "?")
            msg  = body.get("message", "")
            sug  = body.get("suggestion", "")
            raise RuntimeError(f"Tripo3D {step} error {code}: {msg}. {sug}".rstrip(". "))

    # ── Procedural fallback ───────────────────────────────────────────────────

    def _fallback_procedural(self, output_path: str) -> str:
        try:
            import trimesh
        except ImportError:
            raise RuntimeError("trimesh is required for the procedural fallback")

        meshes = []
        body = trimesh.creation.box([14, 10, 7])
        body.apply_translation([0, 0, 3.5])
        body.visual.face_colors = [235, 220, 195, 255]
        meshes.append(body)

        wing = trimesh.creation.box([5, 8, 4])
        wing.apply_translation([9.5, 0, 2])
        wing.visual.face_colors = [230, 215, 190, 255]
        meshes.append(wing)

        roof_verts = np.array([
            [-7, -5, 7], [7, -5, 7], [7, 5, 7], [-7, 5, 7],
            [-5, -3, 11], [5, -3, 11], [5, 3, 11], [-5, 3, 11],
        ], dtype=np.float64)
        roof_faces = np.array([
            [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
            [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7],
            [4, 5, 6], [4, 6, 7],
        ])
        roof = trimesh.Trimesh(vertices=roof_verts, faces=roof_faces, process=False)
        roof.visual.face_colors = [140, 75, 55, 255]
        meshes.append(roof)

        scene = trimesh.Scene()
        for i, m in enumerate(meshes):
            scene.add_geometry(m, node_name=f"part_{i}")
        glb_bytes = scene.export(file_type="glb")
        with open(output_path, "wb") as fh:
            fh.write(glb_bytes)
        logger.info("Procedural fallback GLB saved to %s", output_path)
        return output_path
