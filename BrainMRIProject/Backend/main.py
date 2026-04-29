from pathlib import Path
import base64
import io
import json
import os

import numpy as np
import tensorflow as tf
from fastapi import FastAPI, File, HTTPException, UploadFile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from PIL import Image


app = FastAPI(title="Brain MRI Multi-Disease Detection API")

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
SERVICE_ACCOUNT_FILE = "credentials.json"

FOLDER_ID = "1ggwuI-mpyki0P-a9G2jGC-WQIYX0T9ir"
MODEL_FILE_ID = "15U3oJrBTIurCMCqFFH1JUq-NjMPDyboP"
MODEL_DIR = Path("model")
MODEL_PATH = MODEL_DIR / "final_brain_multi_disease_model.keras"
VALIDATOR_PATH = MODEL_DIR / "mri_validator.keras"
IMAGE_SIZE = (224, 224)
VALIDATOR_IMAGE_SIZE = (128, 128)
MRI_VALIDATION_THRESHOLD = 0.65
CLASS_NAMES = [
    "Healthy Brain",
    "Brain Tumor",
    "Alzheimer's",
    "Multiple Sclerosis (MS)",
]

model = None
validator_model = None


def get_drive_service():
    credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if credentials_json:
        creds = service_account.Credentials.from_service_account_info(
            json.loads(credentials_json),
            scopes=SCOPES,
        )
    else:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES,
        )
    return build("drive", "v3", credentials=creds)


def get_drive_files(folder_id):
    service = get_drive_service()
    results = service.files().list(
        q=f"'{folder_id}' in parents",
        fields="files(id, name, mimeType)",
    ).execute()
    return results.get("files", [])


def get_model():
    global model

    if model is None:
        if not MODEL_PATH.exists():
            raise HTTPException(
                status_code=404,
                detail="Model file is missing. Visit /download-model first.",
            )
        model = tf.keras.models.load_model(MODEL_PATH)

    return model


def get_validator_model():
    global validator_model

    if validator_model is None:
        if not VALIDATOR_PATH.exists():
            return None
        validator_model = tf.keras.models.load_model(VALIDATOR_PATH)

    return validator_model


def prepare_validator_image(file_bytes):
    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read image file.") from exc

    image = image.resize(VALIDATOR_IMAGE_SIZE)
    image_array = np.array(image, dtype=np.float32)
    return np.expand_dims(image_array, axis=0)


def detect_screenshot_or_document(file_bytes):
    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read image file.") from exc

    image.thumbnail((256, 256))
    image_array = np.array(image, dtype=np.float32)
    gray = np.mean(image_array, axis=2)

    bright_fraction = float(np.mean(gray > 235))
    dark_fraction = float(np.mean(gray < 40))
    mid_fraction = float(np.mean((gray >= 40) & (gray <= 235)))

    # Code screenshots and documents usually have large white areas with small dark text.
    # Brain MRI images usually have a dark scan background and far fewer near-white pixels.
    if bright_fraction > 0.45 and dark_fraction < 0.25:
        return {
            "is_rejected": True,
            "reason": "Image looks like a screenshot/document, not a brain MRI scan.",
            "bright_fraction": round(bright_fraction * 100, 2),
            "dark_fraction": round(dark_fraction * 100, 2),
        }

    # Extra guard for plain UI/code captures with mostly light or mid-tone background.
    if bright_fraction > 0.30 and mid_fraction > 0.45 and dark_fraction < 0.20:
        return {
            "is_rejected": True,
            "reason": "Image has screenshot-like brightness patterns.",
            "bright_fraction": round(bright_fraction * 100, 2),
            "dark_fraction": round(dark_fraction * 100, 2),
        }

    return {
        "is_rejected": False,
        "bright_fraction": round(bright_fraction * 100, 2),
        "dark_fraction": round(dark_fraction * 100, 2),
    }


def validate_mri_image(file_bytes):
    screenshot_check = detect_screenshot_or_document(file_bytes)
    if screenshot_check["is_rejected"]:
        return {
            "enabled": True,
            "is_mri": False,
            "mri_probability": 0.0,
            "reason": screenshot_check["reason"],
        }

    loaded_validator = get_validator_model()

    if loaded_validator is None:
        return {
            "enabled": False,
            "is_mri": True,
            "mri_probability": None,
        }

    image = prepare_validator_image(file_bytes)
    prediction = loaded_validator.predict(image, verbose=0)
    mri_probability = float(prediction[0][0])

    return {
        "enabled": True,
        "is_mri": mri_probability >= MRI_VALIDATION_THRESHOLD,
        "mri_probability": round(mri_probability * 100, 2),
        "reason": "MRI validator model prediction",
    }


def prepare_image(file_bytes):
    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read image file.") from exc

    image = image.resize(IMAGE_SIZE)
    image_array = np.array(image, dtype=np.float32)
    image_array = tf.keras.applications.mobilenet_v2.preprocess_input(image_array)
    return np.expand_dims(image_array, axis=0)


def find_last_conv_layer(loaded_model):
    for layer in reversed(loaded_model.layers):
        if isinstance(layer, tf.keras.layers.Conv2D):
            return layer
    return None


def make_heatmap_overlay(file_bytes, class_index):
    loaded_model = get_model()
    base_model = None
    for layer in loaded_model.layers:
        if isinstance(layer, tf.keras.Model):
            base_model = layer
            break

    if base_model is None:
        base_model = loaded_model

    last_conv_layer = find_last_conv_layer(base_model)

    if last_conv_layer is None:
        raise HTTPException(
            status_code=500,
            detail="Could not find a convolution layer for Grad-CAM.",
        )

    image = prepare_image(file_bytes)

    if base_model is loaded_model:
        grad_model = tf.keras.models.Model(
            loaded_model.inputs,
            [last_conv_layer.output, loaded_model.output],
        )
    else:
        classifier_layers = loaded_model.layers[loaded_model.layers.index(base_model) + 1:]
        grad_model = tf.keras.models.Model(
            base_model.inputs,
            [last_conv_layer.output, base_model.output],
        )

    with tf.GradientTape() as tape:
        conv_outputs, model_output = grad_model(image)
        if base_model is loaded_model:
            predictions = model_output
        else:
            predictions = model_output
            for layer in classifier_layers:
                predictions = layer(predictions)

        class_channel = predictions[:, class_index]

    grads = tape.gradient(class_channel, conv_outputs)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
    conv_outputs = conv_outputs[0]
    heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)
    heatmap = tf.maximum(heatmap, 0) / (tf.reduce_max(heatmap) + 1e-8)
    heatmap = heatmap.numpy()

    original = Image.open(io.BytesIO(file_bytes)).convert("RGB").resize(IMAGE_SIZE)
    heatmap_image = Image.fromarray(np.uint8(255 * heatmap)).resize(IMAGE_SIZE)
    heatmap_array = np.array(heatmap_image, dtype=np.float32) / 255.0

    original_array = np.array(original, dtype=np.float32)
    red_heatmap = np.zeros_like(original_array)
    red_heatmap[..., 0] = 255
    red_heatmap[..., 1] = 80 * (1 - heatmap_array)

    alpha = np.expand_dims(heatmap_array * 0.45, axis=2)
    overlay = original_array * (1 - alpha) + red_heatmap * alpha
    overlay = np.clip(overlay, 0, 255).astype(np.uint8)

    output = io.BytesIO()
    Image.fromarray(overlay).save(output, format="PNG")
    return base64.b64encode(output.getvalue()).decode("utf-8")


@app.get("/")
def home():
    return {
        "message": "Brain MRI Detection API is running",
        "docs": "/docs",
        "health": "/health",
        "model_info": "/model-info",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_downloaded": MODEL_PATH.exists(),
        "validator_available": VALIDATOR_PATH.exists(),
        "model_loaded": model is not None,
        "validator_loaded": validator_model is not None,
        "model_path": str(MODEL_PATH),
        "validator_path": str(VALIDATOR_PATH),
    }


@app.get("/files")
def files():
    drive_files = get_drive_files(FOLDER_ID)
    return {
        "count": len(drive_files),
        "files": drive_files,
    }


@app.get("/files/{folder_id}")
def files_in_folder(folder_id: str):
    drive_files = get_drive_files(folder_id)
    return {
        "count": len(drive_files),
        "files": drive_files,
    }


@app.get("/download-model")
def download_model():
    if MODEL_PATH.exists():
        return {
            "message": "Model already downloaded",
            "path": str(MODEL_PATH),
        }

    MODEL_DIR.mkdir(exist_ok=True)
    service = get_drive_service()
    request = service.files().get_media(fileId=MODEL_FILE_ID)

    with MODEL_PATH.open("wb") as model_file:
        downloader = MediaIoBaseDownload(model_file, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

    return {
        "message": "Model downloaded successfully",
        "path": str(MODEL_PATH),
    }


@app.get("/model-info")
def model_info():
    loaded_model = get_model()
    return {
        "model_path": str(MODEL_PATH),
        "input_shape": loaded_model.input_shape,
        "output_shape": loaded_model.output_shape,
        "classes": CLASS_NAMES,
    }


@app.get("/validator-info")
def validator_info():
    loaded_validator = get_validator_model()

    if loaded_validator is None:
        return {
            "available": False,
            "message": "MRI validator model is missing. Run train_mri_validator.py first.",
            "validator_path": str(VALIDATOR_PATH),
        }

    return {
        "available": True,
        "validator_path": str(VALIDATOR_PATH),
        "input_shape": loaded_validator.input_shape,
        "output_shape": loaded_validator.output_shape,
        "threshold": MRI_VALIDATION_THRESHOLD,
        "labels": {
            "0": "Not MRI",
            "1": "MRI",
        },
    }


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a JPG or PNG image.",
        )

    file_bytes = await file.read()
    validation = validate_mri_image(file_bytes)
    if validation["enabled"] and not validation["is_mri"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": validation.get(
                    "reason",
                    "Please upload a valid brain MRI scan. Screenshots, code images, and unrelated photos are not supported.",
                ),
                "mri_probability": validation["mri_probability"],
            },
        )

    image = prepare_image(file_bytes)
    loaded_model = get_model()
    predictions = loaded_model.predict(image, verbose=0)

    scores = predictions[0]
    class_index = int(np.argmax(scores))
    confidence = float(scores[class_index]) * 100

    return {
        "prediction": CLASS_NAMES[class_index],
        "confidence": round(confidence, 2),
        "scores": {
            CLASS_NAMES[index]: round(float(score) * 100, 2)
            for index, score in enumerate(scores)
        },
        "mri_validation": validation,
        "gradcam_overlay": make_heatmap_overlay(file_bytes, class_index),
        "notice": "Educational support tool only. Not a medical diagnosis.",
    }
