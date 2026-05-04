import torch
import clip
from diffusers import StableDiffusionImg2ImgPipeline
from PIL import Image
import numpy as np

# -----------------------------
# CONFIG
# -----------------------------
device = "cpu"

model_id = "runwayml/stable-diffusion-v1-5"

# -----------------------------
# PIPELINE
# -----------------------------
pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
    model_id,
    torch_dtype=torch.float32
).to(device)

pipe.load_lora_weights("lora-villa")

# -----------------------------
# CLIP
# -----------------------------
model, preprocess = clip.load("ViT-B/32", device=device)

# -----------------------------
# PROMPTS (dataset de test)
# -----------------------------
prompts = [
    "modern luxury villa with pool",
    "white modern villa architecture",
    "luxury villa interior living room",
    "modern kitchen in luxury villa",
    "bedroom luxury villa warm lighting"
]

# -----------------------------
# IMAGE FAKE INPUT (img2img besoin)
# -----------------------------
base_image = Image.new("RGB", (256, 256), (200, 200, 200))

# -----------------------------
# CLIP SCORE
# -----------------------------
def clip_score(image, prompt):
    image_input = preprocess(image).unsqueeze(0).to(device)
    text_input = clip.tokenize([prompt]).to(device)

    with torch.no_grad():
        img_feat = model.encode_image(image_input)
        txt_feat = model.encode_text(text_input)

        return torch.cosine_similarity(img_feat, txt_feat).item()

# -----------------------------
# EVALUATION
# -----------------------------
def evaluate_model():
    scores = []

    print("\n🔍 Evaluation en cours...\n")

    for prompt in prompts:

        result = pipe(
            prompt=prompt,
            image=base_image,
            strength=0.65,
            num_inference_steps=30
        ).images[0]

        score = clip_score(result, prompt)
        scores.append(score)

        print(f"Prompt: {prompt}")
        print(f"CLIP Score: {score:.4f}\n")

    print("📊 ===== RESULTAT FINAL =====")
    print(f"CLIP Score moyen: {sum(scores)/len(scores):.4f}")

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    evaluate_model()