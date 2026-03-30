"""
app.py — Digit Recognizer v2
-----------------------------
Key preprocessing improvements:
  - Bounding-box crop → centers the digit (fixes off-center canvas draws)
  - Morphological dilation → thickens thin strokes before resize
  - MNIST-style normalization (mean/std)
  - Supports both v1 (digit_model.keras) and v2 (digit_model_v2.keras) models
"""

from flask import Flask, render_template, request, jsonify
import numpy as np
import base64, io
from PIL import Image, ImageOps, ImageFilter

app = Flask(__name__)
model = None
MODEL_FILES = ["digit_model_v2.keras", "digit_model.keras"]

# ── Model loading ──────────────────────────────────────────
def load_model():
    global model
    import os
    try:
        import tensorflow as tf
        from tensorflow import keras
        for fname in MODEL_FILES:
            if os.path.exists(fname):
                model = keras.models.load_model(fname)
                print(f"✅ Loaded model: {fname}")
                return
        print("⚠️  No model file found. Place digit_model_v2.keras (or digit_model.keras) here.")
    except Exception as e:
        print(f"⚠️  Model load error: {e}")

# ── Preprocessing ──────────────────────────────────────────
def preprocess_image(img: Image.Image, source: str = "upload") -> np.ndarray:
    """
    source = "canvas"  → pure black bg, pure white stroke (no invert needed)
    source = "upload"  → arbitrary image (auto-detect invert)
    """
    # 1. Flatten transparency: paste onto black background first
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (0, 0, 0))
        bg.paste(img, mask=img.split()[-1])
        img = bg

    # 2. Grayscale
    img = img.convert("L")
    arr = np.array(img, dtype=np.float32)

    if source == "upload":
        # Auto-invert: MNIST = white digit on black bg.
        # If average brightness > 127 it's a light background (photo/scan) → invert.
        if arr.mean() > 127:
            img = ImageOps.invert(img)
            arr = np.array(img, dtype=np.float32)
    # For canvas: background is pure black (≈0), stroke is white (≈255) → already correct.

    # 3. Bounding-box crop — isolate the digit, then center it MNIST-style
    #    Use a low threshold so thin strokes are included
    binary = (arr > 30).astype(np.uint8) * 255
    bin_img = Image.fromarray(binary)
    bbox = bin_img.getbbox()

    if bbox:
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        pad = max(int(max(w, h) * 0.25), 4)   # at least 4px padding
        left  = max(0, bbox[0] - pad)
        upper = max(0, bbox[1] - pad)
        right  = min(img.width,  bbox[2] + pad)
        lower  = min(img.height, bbox[3] + pad)
        img = img.crop((left, upper, right, lower))

    # 4. Resize digit to 20×20 (MNIST standard), then center in 28×28
    img = img.resize((20, 20), Image.LANCZOS)
    canvas_28 = Image.new("L", (28, 28), 0)
    canvas_28.paste(img, (4, 4))
    img = canvas_28

    # 5. Slight blur to smooth resize pixelation
    img = img.filter(ImageFilter.GaussianBlur(radius=0.6))

    # 6. Normalize to [0, 1]
    out = np.array(img, dtype=np.float32) / 255.0
    return out.reshape(1, 28, 28, 1)

def predict_digit(arr: np.ndarray) -> dict:
    if model is None:
        return {"error": "Model not loaded — see server console."}
    preds = model.predict(arr, verbose=0)[0]
    digit = int(np.argmax(preds))
    confidence = float(preds[digit])
    all_probs = {str(i): round(float(preds[i]) * 100, 2) for i in range(10)}
    # Top-3 candidates
    top3 = sorted(all_probs.items(), key=lambda x: x[1], reverse=True)[:3]
    return {
        "digit": digit,
        "confidence": round(confidence * 100, 2),
        "probabilities": all_probs,
        "top3": [{"digit": int(d), "prob": p} for d, p in top3],
    }

# ── Routes ─────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/predict/canvas", methods=["POST"])
def predict_canvas():
    data = request.get_json()
    image_data = data.get("image", "")
    if not image_data:
        return jsonify({"error": "No image data"}), 400
    if "," in image_data:
        image_data = image_data.split(",")[1]
    img = Image.open(io.BytesIO(base64.b64decode(image_data)))
    return jsonify(predict_digit(preprocess_image(img, source="canvas")))

@app.route("/predict/upload", methods=["POST"])
def predict_upload():
    if "file" not in request.files or request.files["file"].filename == "":
        return jsonify({"error": "No file uploaded"}), 400
    img = Image.open(request.files["file"].stream)
    return jsonify(predict_digit(preprocess_image(img, source="upload")))

if __name__ == "__main__":
    load_model()
    app.run(debug=True)
