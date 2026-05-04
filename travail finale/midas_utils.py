import torch
import numpy as np
import cv2

def run_midas(image, model):
    """
    image: PIL Image ou np.array HWC
    model: MiDaS pipeline chargé
    retourne: depth map normalisée en numpy array HWC float32
    """
    if not isinstance(image, np.ndarray):
        image = np.array(image)

    img = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    img_input = torch.from_numpy(img / 255.0).permute(2,0,1).unsqueeze(0).float()

    with torch.no_grad():
        depth = model(img_input)[0,0].cpu().numpy()

    # Normaliser pour visualisation
    depth_min = depth.min()
    depth_max = depth.max()
    if depth_max - depth_min > 0:
        depth = (depth - depth_min) / (depth_max - depth_min)
    return depth