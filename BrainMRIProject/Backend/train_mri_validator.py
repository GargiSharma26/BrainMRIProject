from pathlib import Path
import io
import random
import zipfile

import numpy as np
import tensorflow as tf
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from PIL import Image, ImageDraw, ImageFont


SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
SERVICE_ACCOUNT_FILE = "credentials.json"
DATASET_ZIP_FILE_ID = "14YHp7wzdkAGKdAHUKA0NBPTSqqNKyKnK"

WORK_DIR = Path("validator_data")
ZIP_PATH = WORK_DIR / "archive.zip"
EXTRACT_DIR = WORK_DIR / "archive"
TRAIN_DIR = WORK_DIR / "train"
MRI_DIR = TRAIN_DIR / "mri"
NOT_MRI_DIR = TRAIN_DIR / "not_mri"
MODEL_PATH = Path("model") / "mri_validator.keras"

IMAGE_SIZE = (128, 128)
MAX_MRI_IMAGES = 800
EPOCHS = 8
BATCH_SIZE = 32


def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )
    return build("drive", "v3", credentials=creds)


def download_dataset_zip():
    WORK_DIR.mkdir(exist_ok=True)
    if ZIP_PATH.exists():
        print(f"Dataset zip already exists: {ZIP_PATH}")
        return

    print("Downloading MRI dataset archive from Google Drive...")
    service = get_drive_service()
    request = service.files().get_media(fileId=DATASET_ZIP_FILE_ID)

    with ZIP_PATH.open("wb") as output:
        downloader = MediaIoBaseDownload(output, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"Download progress: {int(status.progress() * 100)}%")


def extract_dataset_zip():
    if EXTRACT_DIR.exists() and any(EXTRACT_DIR.rglob("*")):
        print(f"Dataset already extracted: {EXTRACT_DIR}")
        return

    print("Extracting dataset archive...")
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH) as archive:
        archive.extractall(EXTRACT_DIR)


def collect_image_paths():
    image_paths = []
    for pattern in ("*.jpg", "*.jpeg", "*.png", "*.bmp"):
        image_paths.extend(EXTRACT_DIR.rglob(pattern))

    random.shuffle(image_paths)
    return image_paths[:MAX_MRI_IMAGES]


def save_mri_training_images(image_paths):
    MRI_DIR.mkdir(parents=True, exist_ok=True)

    saved = 0
    for path in image_paths:
        try:
            image = Image.open(path).convert("RGB")
            image.thumbnail(IMAGE_SIZE)
            canvas = Image.new("RGB", IMAGE_SIZE, "black")
            x = (IMAGE_SIZE[0] - image.width) // 2
            y = (IMAGE_SIZE[1] - image.height) // 2
            canvas.paste(image, (x, y))
            canvas.save(MRI_DIR / f"mri_{saved:04d}.jpg", quality=90)
            saved += 1
        except Exception:
            continue

    print(f"Prepared MRI images: {saved}")
    return saved


def create_code_like_image(index):
    image = Image.new("RGB", IMAGE_SIZE, "white")
    draw = ImageDraw.Draw(image)
    code_lines = [
        "public class Main {",
        "  public static void main(String[] args) {",
        "    System.out.println(\"Hello\");",
        "    for (int i = 0; i < 10; i++) {",
        "      total += i;",
        "    }",
        "  }",
        "}",
    ]
    y = 8
    for line in code_lines:
        draw.text((8, y), line, fill=(20, 20, 20), font=ImageFont.load_default())
        y += 14
    return image


def create_document_like_image(index):
    image = Image.new("RGB", IMAGE_SIZE, (245, 246, 248))
    draw = ImageDraw.Draw(image)
    for y in range(12, 118, 14):
        width = random.randint(60, 110)
        draw.rectangle((10, y, 10 + width, y + 4), fill=(80, 88, 100))
    return image


def create_noise_image(index):
    array = np.random.randint(0, 255, (IMAGE_SIZE[1], IMAGE_SIZE[0], 3), dtype=np.uint8)
    return Image.fromarray(array, "RGB")


def create_shape_image(index):
    image = Image.new(
        "RGB",
        IMAGE_SIZE,
        tuple(np.random.randint(30, 230, 3).tolist()),
    )
    draw = ImageDraw.Draw(image)
    for _ in range(12):
        x1 = random.randint(0, IMAGE_SIZE[0] - 20)
        y1 = random.randint(0, IMAGE_SIZE[1] - 20)
        x2 = random.randint(x1 + 10, IMAGE_SIZE[0])
        y2 = random.randint(y1 + 10, IMAGE_SIZE[1])
        color = tuple(np.random.randint(0, 255, 3).tolist())
        draw.rectangle((x1, y1, x2, y2), outline=color, width=2)
    return image


def generate_not_mri_images(count):
    NOT_MRI_DIR.mkdir(parents=True, exist_ok=True)
    generators = [
        create_code_like_image,
        create_document_like_image,
        create_noise_image,
        create_shape_image,
    ]

    for index in range(count):
        generator = generators[index % len(generators)]
        image = generator(index)
        image.save(NOT_MRI_DIR / f"not_mri_{index:04d}.jpg", quality=90)

    print(f"Prepared non-MRI images: {count}")


def build_validator_model():
    return tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(IMAGE_SIZE[1], IMAGE_SIZE[0], 3)),
            tf.keras.layers.Rescaling(1.0 / 255),
            tf.keras.layers.Conv2D(16, 3, activation="relu"),
            tf.keras.layers.MaxPooling2D(),
            tf.keras.layers.Conv2D(32, 3, activation="relu"),
            tf.keras.layers.MaxPooling2D(),
            tf.keras.layers.Conv2D(64, 3, activation="relu"),
            tf.keras.layers.MaxPooling2D(),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(64, activation="relu"),
            tf.keras.layers.Dense(1, activation="sigmoid"),
        ]
    )


def train_validator():
    train_dataset = tf.keras.utils.image_dataset_from_directory(
        TRAIN_DIR,
        labels="inferred",
        label_mode="binary",
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        validation_split=0.2,
        subset="training",
        seed=42,
    )
    validation_dataset = tf.keras.utils.image_dataset_from_directory(
        TRAIN_DIR,
        labels="inferred",
        label_mode="binary",
        image_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        validation_split=0.2,
        subset="validation",
        seed=42,
    )

    model = build_validator_model()
    model.compile(
        optimizer="adam",
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    model.fit(
        train_dataset,
        validation_data=validation_dataset,
        epochs=EPOCHS,
    )

    MODEL_PATH.parent.mkdir(exist_ok=True)
    model.save(MODEL_PATH)
    print(f"Saved MRI validator model: {MODEL_PATH}")


def main():
    random.seed(42)
    np.random.seed(42)
    tf.random.set_seed(42)

    download_dataset_zip()
    extract_dataset_zip()

    image_paths = collect_image_paths()
    if not image_paths:
        raise RuntimeError("No MRI images found in the extracted dataset.")

    mri_count = save_mri_training_images(image_paths)
    generate_not_mri_images(mri_count)
    train_validator()


if __name__ == "__main__":
    main()
