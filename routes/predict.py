# routes/predict.py
import os, uuid, base64, io
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from PIL import Image, ImageOps, ImageFilter
import numpy as np
from extensions import db
from models import Prediction

predict_bp = Blueprint("predict", __name__)

model = None
MODEL_FILES = ["model/digit_model_v2.keras", "model/digit_model.keras"]


def load_model():
    global model
    try:
        import tensorflow as tf
        from tensorflow import keras
        for fname in MODEL_FILES:
            if os.path.exists(fname):
                model = keras.models.load_model(fname)
                print(f"✅ Loaded model: {fname}")
                return
        print("⚠️  No model file found.")
    except Exception as e:
        print(f"⚠️  Model load error: {e}")


def preprocess_image(img: Image.Image, source: str = "upload") -> np.ndarray:
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (0, 0, 0))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    img = img.convert("L")
    arr = np.array(img, dtype=np.float32)
    if source == "upload":
        if arr.mean() > 127:
            img = ImageOps.invert(img)
            arr = np.array(img, dtype=np.float32)
    binary = (arr > 30).astype(np.uint8) * 255
    bin_img = Image.fromarray(binary)
    bbox = bin_img.getbbox()
    if bbox:
        w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
        pad   = max(int(max(w, h) * 0.25), 4)
        left  = max(0, bbox[0]-pad); upper = max(0, bbox[1]-pad)
        right = min(img.width, bbox[2]+pad); lower = min(img.height, bbox[3]+pad)
        img   = img.crop((left, upper, right, lower))
    img = img.resize((20, 20), Image.LANCZOS)
    canvas_28 = Image.new("L", (28, 28), 0)
    canvas_28.paste(img, (4, 4))
    img = canvas_28.filter(ImageFilter.GaussianBlur(radius=0.6))
    out = np.array(img, dtype=np.float32) / 255.0
    return out.reshape(1, 28, 28, 1)


def run_prediction(arr: np.ndarray) -> dict:
    if model is None:
        return {"error": "Model not loaded."}
    preds      = model.predict(arr, verbose=0)[0]
    digit      = int(np.argmax(preds))
    confidence = float(preds[digit])
    all_probs  = {str(i): round(float(preds[i]) * 100, 2) for i in range(10)}
    top3       = sorted(all_probs.items(), key=lambda x: x[1], reverse=True)[:3]
    return {
        "digit":       digit,
        "confidence":  round(confidence * 100, 2),
        "probabilities": all_probs,
        "top3": [{"digit": int(d), "prob": p} for d, p in top3],
    }


def save_snapshot(image_data_b64: str, upload_folder: str) -> str:
    """Save base64 PNG canvas image to disk, return filename."""
    os.makedirs(upload_folder, exist_ok=True)
    fname = f"{uuid.uuid4().hex}.png"
    fpath = os.path.join(upload_folder, fname)
    img_bytes = base64.b64decode(image_data_b64)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img = img.resize((140, 140), Image.LANCZOS)   # compact thumbnail
    img.save(fpath, "PNG")
    return fname


@predict_bp.route("/predict/canvas", methods=["POST"])
@login_required
def predict_canvas():
    from flask import current_app
    data       = request.get_json()
    image_data = data.get("image", "")
    if not image_data:
        return jsonify({"error": "No image data"}), 400

    b64 = image_data.split(",")[1] if "," in image_data else image_data
    img = Image.open(io.BytesIO(base64.b64decode(b64)))
    result = run_prediction(preprocess_image(img, source="canvas"))

    if "error" not in result:
        folder   = current_app.config["UPLOAD_FOLDER"]
        snapshot = save_snapshot(b64, folder)
        pred = Prediction(
            user_id=current_user.id, digit=result["digit"],
            confidence=result["confidence"], top3=result["top3"],
            snapshot=snapshot, source="canvas",
        )
        db.session.add(pred)
        db.session.commit()
        result["prediction_id"] = pred.id

    return jsonify(result)


@predict_bp.route("/predict/upload", methods=["POST"])
@login_required
def predict_upload():
    if "file" not in request.files or request.files["file"].filename == "":
        return jsonify({"error": "No file uploaded"}), 400
    img    = Image.open(request.files["file"].stream)
    result = run_prediction(preprocess_image(img, source="upload"))

    if "error" not in result:
        pred = Prediction(
            user_id=current_user.id, digit=result["digit"],
            confidence=result["confidence"], top3=result["top3"],
            snapshot=None, source="upload",
        )
        db.session.add(pred)
        db.session.commit()
        result["prediction_id"] = pred.id

    return jsonify(result)