"""
Shared CLIP-based hazard classification logic.

Both the desktop script (webcam_detect.py) and the web API (server.py)
import from here, so the label list and model-loading code only exist once.
"""

import torch
from transformers import CLIPModel, CLIPProcessor

MODEL_NAME = "openai/clip-vit-base-patch32"

# Candidate scene descriptions. CLIP scores an image against every one of
# these and returns the closest match. Add/remove/edit freely — no
# retraining needed, just change the text. Keep a healthy number of
# "normal" labels too — CLIP always picks ONE best match out of the whole
# list, so without enough normal options it will over-eagerly pick a hazard.
LABELS = [
    "a photo of an active fire with visible orange flames",
    "a photo of thick black or grey smoke",
    "a photo of a flooded street or room with standing water",
    "a photo of a deep pothole or large crack on a paved road",
    "a photo of a smooth, undamaged paved road or street",
    "a photo of two people physically fighting or hitting each other",
    "a photo of a car crash or traffic accident with damaged vehicles",
    "a photo of a person lying injured on the ground",
    "a photo of people calmly standing, walking, or talking",
    "a photo of a normal indoor room",
    "a photo of a normal outdoor scene with no damage or danger",
    "a photo of a dark or empty room",
]

# Which of the labels above should be treated as a hazard, and the short tag
# to show/report for each. Any label NOT in this dict is treated as "normal".
# NOTE: these strings must match LABELS above *exactly* (word-for-word) —
# HAZARD_LABELS.get(label) is a plain dict lookup, so even a one-word mismatch
# (e.g. "in a road" vs "on a road") silently means that hazard is never
# tagged, no matter how confident the model is. This bit us for potholes.
HAZARD_LABELS = {
    "a photo of an active fire with visible orange flames": "FIRE",
    "a photo of thick black or grey smoke": "SMOKE",
    "a photo of a flooded street or room with standing water": "FLOOD",
    "a photo of a deep pothole or large crack on a paved road": "POTHOLE",
    "a photo of two people physically fighting or hitting each other": "FIGHT",
    "a photo of a car crash or traffic accident with damaged vehicles": "ACCIDENT",
    "a photo of a person lying injured on the ground": "INJURY",
}

# Raised from 0.45: at the lower threshold, CLIP's best-of-12 guess was often
# shown as a confident hazard suggestion even when it wasn't a strong match
# for anything in particular. At 0.55 the app more often falls back to "no
# clear hazard detected, choose a category manually" instead of guessing.
CONFIDENCE_THRESHOLD = 0.55  # minimum CLIP probability to trust a label as a hazard

_model = None
_processor = None
_device = None


def load_model():
    """Load the CLIP model once. Safe to call multiple times (cached after first call)."""
    global _model, _processor, _device
    if _model is None:
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading CLIP model on {_device}... (first run downloads ~350MB, be patient)")
        _model = CLIPModel.from_pretrained(MODEL_NAME).to(_device).eval()
        _processor = CLIPProcessor.from_pretrained(MODEL_NAME)
        print("Model loaded.")
    return _model, _processor, _device


@torch.no_grad()
def classify_frame(pil_image):
    """
    Classify a PIL image against LABELS.

    Returns (label: str, confidence: float, hazard_tag: str | None).
    hazard_tag is None unless the best label is a hazard AND its confidence
    is >= CONFIDENCE_THRESHOLD.
    """
    model, processor, device = load_model()
    inputs = processor(text=LABELS, images=pil_image, return_tensors="pt", padding=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    outputs = model(**inputs)
    probs = outputs.logits_per_image.softmax(dim=1)[0]
    best_idx = int(probs.argmax())
    label = LABELS[best_idx]
    confidence = float(probs[best_idx])
    tag = HAZARD_LABELS.get(label) if confidence >= CONFIDENCE_THRESHOLD else None
    return label, confidence, tag
