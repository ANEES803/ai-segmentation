# model_loader.py

import os
from segment_anything import sam_model_registry, SamPredictor
import torch

def load_sam_model():
    model_type = "vit_b"

    # ✅ Correct path if model is inside `django rock/models/`
    checkpoint_path = os.path.join("C:/Users/Mg/Desktop/django rock2/models", "sam_vit_b_01ec64.pth")

    sam = sam_model_registry[model_type](checkpoint=checkpoint_path)
    sam.eval()
    predictor = SamPredictor(sam)
    return predictor
