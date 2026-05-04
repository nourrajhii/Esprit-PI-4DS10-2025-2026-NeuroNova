import os
import torch
import clip
from PIL import Image
from cleanfid import fid
import multiprocessing

# -----------------------------
# FIX WINDOWS (IMPORTANT)
# -----------------------------
if __name__ == "__main__":
    multiprocessing.freeze_support()

# -----------------------------
# PATHS
# -----------------------------
DATASET_IMAGES_PATH = "dataset_images"
OUTPUT_PATH = "terrain2/output"
PROMPTS_FILE = "prompts.txt"

device = "cuda" if torch.cuda.is_available() else "cpu"

# -----------------------------
# LOAD CLIP
# -----------------------------
print("Loading CLIP model...")
model, preprocess = clip.load("ViT-B/32", device=device)

# -----------------------------
# LOAD PROMPTS
# -----------------------------
def load_prompts():
    with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
        prompts = [line.strip() for line in f.readlines() if line.strip()]
    return prompts

# -----------------------------
# CLIP SCORE
# -----------------------------
def compute_clip_score():
    print("\n🧠 Calcul CLIP Score...")

    prompts = load_prompts()
    images = sorted(os.listdir(OUTPUT_PATH))

    scores = []

    for i, img_name in enumerate(images):

        if i >= len(prompts):
            break

        try:
            img_path = os.path.join(OUTPUT_PATH, img_name)

            image = preprocess(Image.open(img_path).convert("RGB")).unsqueeze(0).to(device)
            text = clip.tokenize([prompts[i]]).to(device)

            with torch.no_grad():
                img_feat = model.encode_image(image)
                txt_feat = model.encode_text(text)

                score = torch.cosine_similarity(img_feat, txt_feat)

            scores.append(score.item())

            print(f"{img_name} -> {score.item():.4f}")

        except Exception as e:
            print(f"Erreur {img_name}: {e}")

    if len(scores) == 0:
        return 0

    return sum(scores) / len(scores)

# -----------------------------
# FID SCORE (CLEAN DATASET)
# -----------------------------
def compute_fid_score():
    print("\n📊 Calcul FID...")

    if not os.path.exists(DATASET_IMAGES_PATH):
        return "❌ dataset_images introuvable"

    if not os.path.exists(OUTPUT_PATH):
        return "❌ output introuvable"

    score = fid.compute_fid(
        DATASET_IMAGES_PATH,
        OUTPUT_PATH,
        num_workers=0   # FIX WINDOWS CRASH
    )

    return score

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":

    print("\n🚀 ===== EVALUATION LO-RA MODEL =====\n")

    # CLIP
    clip_score = compute_clip_score()
    print(f"\n📌 CLIP SCORE MOYEN : {clip_score:.4f}")

    # FID
    fid_score = compute_fid_score()
    print(f"\n📌 FID SCORE : {fid_score}")

    print("\n✅ Evaluation terminée")