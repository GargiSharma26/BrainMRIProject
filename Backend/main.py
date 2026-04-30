from pathlib import Path
import base64
import csv
from datetime import datetime, timezone
import io
import json
import os
import sqlite3
from typing import Any

import numpy as np
import tensorflow as tf
from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from PIL import Image
from pydantic import BaseModel, Field


app = FastAPI(title="Brain MRI Multi-Disease Detection API")

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
SERVICE_ACCOUNT_FILE = "credentials.json"

FOLDER_ID = "1ggwuI-mpyki0P-a9G2jGC-WQIYX0T9ir"
MODEL_FILE_ID = "15U3oJrBTIurCMCqFFH1JUq-NjMPDyboP"
MODEL_DIR = Path("model")
MODEL_PATH = MODEL_DIR / "final_brain_multi_disease_model.keras"
VALIDATOR_PATH = MODEL_DIR / "mri_validator.keras"
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "brain_mri_records.db"))
IMAGE_SIZE = (224, 224)
VALIDATOR_IMAGE_SIZE = (128, 128)
MRI_VALIDATION_THRESHOLD = 0.65
MIN_MRI_LIKENESS_SCORE = 2
CLASS_NAMES = [
    "Healthy Brain",
    "Alzheimer's",
    "Brain Tumor",
    "Multiple Sclerosis (MS)",
]

model = None
validator_model = None


class PatientRecord(BaseModel):
    patient_name: str = Field(..., min_length=1, max_length=120)
    age: int = Field(..., ge=1, le=120)
    condition: str = Field(..., min_length=1, max_length=120)
    symptoms: str = ""
    prediction: str = Field(..., min_length=1, max_length=120)
    confidence: float = Field(..., ge=0, le=100)
    scores: dict[str, float] = Field(default_factory=dict)
    mri_validation: dict[str, Any] = Field(default_factory=dict)


def get_db_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS patient_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name TEXT NOT NULL,
                age INTEGER NOT NULL,
                condition TEXT NOT NULL,
                symptoms TEXT,
                prediction TEXT NOT NULL,
                confidence REAL NOT NULL,
                scores_json TEXT NOT NULL,
                mri_validation_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


@app.on_event("startup")
def startup_event():
    init_database()


def get_drive_service():
    credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    try:
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
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Google Drive credentials are not configured. Add credentials.json "
                "locally or set GOOGLE_CREDENTIALS_JSON on Render."
            ),
        ) from exc
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
    if bright_fraction > 0.70 and dark_fraction < 0.12:
        return {
            "is_rejected": True,
            "reason": "Image looks like a screenshot/document, not a brain MRI scan.",
            "bright_fraction": round(bright_fraction * 100, 2),
            "dark_fraction": round(dark_fraction * 100, 2),
        }

    # Extra guard for plain UI/code captures with mostly light or mid-tone background.
    if bright_fraction > 0.55 and mid_fraction > 0.35 and dark_fraction < 0.12:
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


def estimate_mri_likeness(file_bytes):
    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read image file.") from exc

    original_width, original_height = image.size
    aspect_ratio = original_width / max(original_height, 1)

    image.thumbnail((256, 256))
    image_array = np.array(image, dtype=np.float32)
    gray = np.mean(image_array, axis=2)
    channel_spread = np.mean(np.max(image_array, axis=2) - np.min(image_array, axis=2))

    dark_fraction = float(np.mean(gray < 45))
    bright_fraction = float(np.mean(gray > 180))
    center = gray[
        gray.shape[0] // 4 : gray.shape[0] * 3 // 4,
        gray.shape[1] // 4 : gray.shape[1] * 3 // 4,
    ]
    center_contrast = float(np.std(center))
    foreground_mask = gray > 35
    foreground_fraction = float(np.mean(foreground_mask))

    if np.any(foreground_mask):
        ys, xs = np.where(foreground_mask)
        bbox_width = (int(xs.max()) - int(xs.min()) + 1) / gray.shape[1]
        bbox_height = (int(ys.max()) - int(ys.min()) + 1) / gray.shape[0]
        bbox_center_x = (int(xs.min()) + int(xs.max())) / (2 * gray.shape[1])
        bbox_center_y = (int(ys.min()) + int(ys.max())) / (2 * gray.shape[0])
    else:
        bbox_width = 0.0
        bbox_height = 0.0
        bbox_center_x = 0.0
        bbox_center_y = 0.0

    aspect_ok = 0.75 <= aspect_ratio <= 1.35
    grayscale_ok = channel_spread < 22
    structure_ok = (
        dark_fraction > 0.20
        and bright_fraction > 0.06
        and center_contrast > 18
        and foreground_fraction > 0.20
        and bbox_width > 0.45
        and bbox_height > 0.45
        and abs(bbox_center_x - 0.5) < 0.18
        and abs(bbox_center_y - 0.5) < 0.18
    )

    score = 0
    reasons = []

    if aspect_ok:
        score += 1
        reasons.append("near-square scan image")
    if grayscale_ok:
        score += 1
        reasons.append("mostly grayscale")
    if dark_fraction > 0.20:
        score += 1
        reasons.append("dark MRI-like background")
    if bright_fraction > 0.06:
        score += 1
        reasons.append("visible bright tissue structure")
    if center_contrast > 18:
        score += 1
        reasons.append("brain-like internal contrast")
    if structure_ok:
        score += 1
        reasons.append("centered scan structure")

    return {
        "score": score,
        "is_likely_mri": aspect_ok and grayscale_ok and structure_ok and score >= 5,
        "reasons": reasons,
        "width": original_width,
        "height": original_height,
        "aspect_ratio": round(float(aspect_ratio), 3),
        "channel_spread": round(float(channel_spread), 2),
        "dark_fraction": round(dark_fraction * 100, 2),
        "bright_fraction": round(bright_fraction * 100, 2),
        "center_contrast": round(center_contrast, 2),
        "foreground_fraction": round(foreground_fraction * 100, 2),
        "foreground_bbox_width": round(float(bbox_width), 3),
        "foreground_bbox_height": round(float(bbox_height), 3),
    }


def validate_mri_image(file_bytes):
    screenshot_check = detect_screenshot_or_document(file_bytes)
    likeness = estimate_mri_likeness(file_bytes)

    if not likeness["is_likely_mri"]:
        return {
            "enabled": True,
            "is_mri": False,
            "validator_passed": False,
            "mri_probability": None,
            "reason": "Irrelevant image detected. Please upload a clear brain MRI scan.",
            "likeness": likeness,
        }

    if screenshot_check["is_rejected"]:
        return {
            "enabled": True,
            "is_mri": False,
            "validator_passed": False,
            "mri_probability": None,
            "reason": "Irrelevant image detected. Please upload the MRI scan image itself, not a document or screenshot.",
            "likeness": likeness,
        }

    loaded_validator = get_validator_model()

    if loaded_validator is None:
        return {
            "enabled": False,
            "is_mri": True,
            "mri_probability": None,
            "likeness": likeness,
        }

    image = prepare_validator_image(file_bytes)
    prediction = loaded_validator.predict(image, verbose=0)
    mri_probability = float(prediction[0][0])
    is_confident_mri = mri_probability >= MRI_VALIDATION_THRESHOLD

    return {
        "enabled": True,
        "is_mri": True,
        "validator_passed": is_confident_mri,
        "mri_probability": round(mri_probability * 100, 2),
        "reason": (
            "MRI validator model prediction"
            if is_confident_mri
            else "MRI validator confidence is low, so it is shown as a warning and the disease model still runs."
        ),
        "likeness": likeness,
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


def colorize_heatmap(heatmap_array):
    clipped = np.clip(heatmap_array, 0.0, 1.0)

    red = np.clip(3.0 * clipped - 0.7, 0.0, 1.0)
    green = np.clip(3.0 * clipped - 0.25, 0.0, 1.0)
    blue = np.clip(1.2 - 2.4 * clipped, 0.0, 1.0)

    colorized = np.stack([red, green, blue], axis=-1)

    # Push the highest-attention regions toward white after they become yellow.
    white_boost = np.clip((clipped - 0.82) / 0.18, 0.0, 1.0)
    colorized = colorized * (1 - white_boost[..., None]) + white_boost[..., None]

    return (colorized * 255).astype(np.uint8)


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
    colored_heatmap = colorize_heatmap(heatmap_array).astype(np.float32)

    alpha = np.expand_dims(0.25 + heatmap_array * 0.50, axis=2)
    overlay = original_array * (1 - alpha) + colored_heatmap * alpha
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
        "database_path": str(DATABASE_PATH),
        "database_ready": DATABASE_PATH.exists(),
    }


@app.post("/patient-records")
def create_patient_record(record: PatientRecord):
    init_database()
    created_at = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO patient_records (
                patient_name,
                age,
                condition,
                symptoms,
                prediction,
                confidence,
                scores_json,
                mri_validation_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.patient_name,
                record.age,
                record.condition,
                record.symptoms,
                record.prediction,
                record.confidence,
                json.dumps(record.scores),
                json.dumps(record.mri_validation),
                created_at,
            ),
        )
        record_id = cursor.lastrowid

    return {
        "message": "Patient record saved",
        "id": record_id,
        "created_at": created_at,
    }


@app.get("/patient-records")
def list_patient_records():
    init_database()
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                patient_name,
                age,
                condition,
                symptoms,
                prediction,
                confidence,
                scores_json,
                mri_validation_json,
                created_at
            FROM patient_records
            ORDER BY id DESC
            LIMIT 100
            """
        ).fetchall()

    records = []
    for row in rows:
        records.append(
            {
                "id": row["id"],
                "patient_name": row["patient_name"],
                "age": row["age"],
                "condition": row["condition"],
                "symptoms": row["symptoms"],
                "prediction": row["prediction"],
                "confidence": row["confidence"],
                "scores": json.loads(row["scores_json"]),
                "mri_validation": json.loads(row["mri_validation_json"]),
                "created_at": row["created_at"],
            }
        )

    return {
        "count": len(records),
        "records": records,
    }


@app.get("/patient-records.csv")
def export_patient_records_csv():
    init_database()
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                patient_name,
                age,
                condition,
                symptoms,
                prediction,
                confidence,
                scores_json,
                mri_validation_json,
                created_at
            FROM patient_records
            ORDER BY id DESC
            """
        ).fetchall()

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id",
            "patient_name",
            "age",
            "condition",
            "symptoms",
            "prediction",
            "confidence",
            "healthy_brain_score",
            "brain_tumor_score",
            "alzheimers_score",
            "multiple_sclerosis_score",
            "mri_probability",
            "validator_passed",
            "validation_reason",
            "created_at",
        ],
    )
    writer.writeheader()

    for row in rows:
        scores = json.loads(row["scores_json"])
        validation = json.loads(row["mri_validation_json"])
        writer.writerow(
            {
                "id": row["id"],
                "patient_name": row["patient_name"],
                "age": row["age"],
                "condition": row["condition"],
                "symptoms": row["symptoms"],
                "prediction": row["prediction"],
                "confidence": row["confidence"],
                "healthy_brain_score": scores.get("Healthy Brain"),
                "brain_tumor_score": scores.get("Brain Tumor"),
                "alzheimers_score": scores.get("Alzheimer's"),
                "multiple_sclerosis_score": scores.get("Multiple Sclerosis (MS)"),
                "mri_probability": validation.get("mri_probability"),
                "validator_passed": validation.get("validator_passed"),
                "validation_reason": validation.get("reason"),
                "created_at": row["created_at"],
            }
        )

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=patient_records.csv"},
    )


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
                    "Irrelevant image detected. Please upload a clear brain MRI scan.",
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
