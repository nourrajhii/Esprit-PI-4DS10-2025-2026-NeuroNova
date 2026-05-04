import torch
from diffusers import StableDiffusionImg2ImgPipeline
import gradio as gr
from PIL import Image
import numpy as np
import open3d as o3d
import os
from datetime import datetime

# -----------------------------
# Dossier de sauvegarde
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------
# Chargement modèle 2D
# -----------------------------
model_id = "runwayml/stable-diffusion-v1-5"

pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
    model_id,
    torch_dtype=torch.float32
)

pipe.load_lora_weights("lora-villa")
pipe = pipe.to("cpu")

generated_global = None


# -----------------------------
# Génération 2D + sauvegarde
# -----------------------------
def generate(image, prompt):
    global generated_global

    if image is None:
        return None

    image = image.resize((256, 256))

    result = pipe(
        prompt=prompt,
        image=image,
        strength=0.65,
        num_inference_steps=30
    ).images[0]

    generated_global = result

    # -----------------------------
    # Sauvegarde image output
    # -----------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"villa_{timestamp}.png"
    path = os.path.join(OUTPUT_DIR, filename)

    result.save(path)

    print(f"[SAVED] {path}")

    return result


# -----------------------------
# Conversion 2D -> 3D
# -----------------------------
def view_3d():
    global generated_global

    if generated_global is None:
        return "❌ Generate image first"

    image = generated_global

    depth = np.array(image.convert("L")) / 255.0
    image_np = np.array(image)

    h, w = depth.shape

    vertices = []
    colors = []
    triangles = []

    for y in range(h):
        for x in range(w):
            z = depth[y, x] * 10
            vertices.append([x, -y, z])
            colors.append(image_np[y, x] / 255.0)

    for y in range(h - 1):
        for x in range(w - 1):
            i = y * w + x
            triangles.append([i, i + 1, i + w])
            triangles.append([i + 1, i + w + 1, i + w])

    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(vertices)
    mesh.triangles = o3d.utility.Vector3iVector(triangles)
    mesh.vertex_colors = o3d.utility.Vector3dVector(colors)

    mesh.compute_vertex_normals()

    o3d.visualization.draw_geometries([mesh])

    return "✅ 3D opened"


# -----------------------------
# Interface Gradio
# -----------------------------
with gr.Blocks() as demo:
    gr.Markdown("# 🏡 Villa Generator + 3D + Dataset Saver")

    with gr.Row():
        input_image = gr.Image(type="pil", label="Input Image")
        prompt_input = gr.Textbox(
            label="Prompt",
            placeholder="Ex: modern luxury villa, pool, sunset, cinematic"
        )
        output_image = gr.Image(label="Generated Image")

    generate_btn = gr.Button("Generate 2D")
    view3d_btn = gr.Button("Visualiser en 3D")

    status = gr.Textbox()

    generate_btn.click(
        fn=generate,
        inputs=[input_image, prompt_input],
        outputs=output_image
    )

    view3d_btn.click(
        fn=view_3d,
        inputs=None,
        outputs=status
    )

demo.launch()