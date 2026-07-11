"""
Download PlantVillage dataset from Kaggle and prepare for training.

Usage:
    python -m app.models_ml.training.prepare_plantvillage

Downloads to: data/raw/plantvillage/
Prepares to: data/prepared/{crop}/train|val|test/{class}/
"""

import logging
import random
import shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = Path("data/raw/plantvillage")
PREPARED_DIR = Path("data/prepared")

PLANTVILLAGE_TO_OURS = {
    "Rice": {
        "Rice___Bacterial_leaf_blight": "Bacterial Leaf Blight",
        "Rice___Brown_spot": "Brown Spot",
        "Rice___healthy": "Healthy",
        "Rice___Hispa": "Leaf Sheath Blight",
        "Rice___Leaf_Blast": "Rice Blast",
        "Rice___Leaf_scald": "Rice Blast",
        "Rice___Sheath_Blight": "Leaf Sheath Blight",
        "Rice___Tungro": "Tungro",
    },
    "Tomato": {
        "Tomato_Bacterial_spot": "Bacterial Spot",
        "Tomato_Early_blight": "Early Blight",
        "Tomato_Late_blight": "Late Blight",
        "Tomato_Leaf_Mold": "Leaf Mold",
        "Tomato_Septoria_leaf_spot": "Septoria Leaf Spot",
        "Tomato_Spider_mites_Two_spotted_spider_mite": "Spider Mites",
        "Tomato__Target_Spot": "Target Spot",
        "Tomato__Tomato_YellowLeaf__Curl_Virus": "Yellow Leaf Curl Virus",
        "Tomato__Tomato_mosaic_virus": "Tomato Mosaic Virus",
        "Tomato_healthy": "Healthy",
    },
    "Potato": {
        "Potato___Early_blight": "Early Blight",
        "Potato___Late_blight": "Late Blight",
        "Potato___healthy": "Healthy",
    },
    "Corn": {
        "Corn_(maize)___Common_rust_": "Common Rust",
        "Corn_(maize)___Northern_Leaf_Blight": "Northern Leaf Blight",
        "Corn_(maize)___Gray_Leaf_Spot": "Gray Leaf Spot",
        "Corn_(maize)___healthy": "Healthy",
    },
    "Grape": {
        "Grape___Black_rot": "Black Rot",
        "Grape___Esca_(Black_Measles)": "Black Rot",
        "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": "Leaf Blight",
        "Grape___healthy": "Healthy",
    },
    "Pepper": {
        "Pepper__bell___Bacterial_spot": "Bacterial Spot",
        "Pepper__bell___healthy": "Healthy",
    },
    "Apple": {
        "Apple___Apple_scab": "Black Rot",
        "Apple___Black_rot": "Black Rot",
        "Apple___Cedar_apple_rust": "Leaf Blight",
        "Apple___healthy": "Healthy",
    },
    "Cherry": {
        "Cherry_(including_sour)___Powdery_mildew": "Powdery Mildew",
        "Cherry_(including_sour)___healthy": "Healthy",
    },
    "Orange": {
        "Orange___Haunglongbing_(Citrus_greening)": "Bacterial Spot",
    },
    "Peach": {
        "Peach___Bacterial_spot": "Bacterial Spot",
        "Peach___healthy": "Healthy",
    },
    "Blueberry": {
        "Blueberry___healthy": "Healthy",
    },
    "Squash": {
        "Squash___Powdery_mildew": "Powdery Mildew",
    },
}

RICE_RAW_DIR = Path("data/raw/rice-disease")

RICE_MAPPING = {
    "Bacterial leaf blight": "Bacterial Leaf Blight",
    "Blast": "Rice Blast",
    "Brown spot": "Brown Spot",
    "Leaf smut": "Leaf Smut",
    "Tungro": "Tungro",
}

TRAIN_RATIO = 0.8
VAL_RATIO = 0.1
TEST_RATIO = 0.1


def download_plantvillage():
    if RAW_DIR.exists() and any(RAW_DIR.iterdir()):
        logger.info("PlantVillage dataset already exists at %s, skipping", RAW_DIR)
        return

    logger.info("Downloading PlantVillage dataset from Kaggle...")
    try:
        import kagglehub

        path = kagglehub.dataset_download("emmarex/plantdisease", force_download=False)
        logger.info("Downloaded to: %s", path)

        RAW_DIR.parent.mkdir(parents=True, exist_ok=True)
        if RAW_DIR.exists():
            shutil.rmtree(RAW_DIR)
        shutil.move(str(path), str(RAW_DIR))
        logger.info("Moved to: %s", RAW_DIR)
    except Exception as e:
        logger.error("Download failed: %s", e)


def download_rice():
    if RICE_RAW_DIR.exists() and any(RICE_RAW_DIR.iterdir()):
        logger.info("Rice dataset already exists at %s, skipping", RICE_RAW_DIR)
        return

    logger.info("Downloading rice disease dataset from Kaggle...")
    try:
        import kagglehub

        path = kagglehub.dataset_download(
            "sasi89143/rice-leaf-disease-dataset", force_download=False
        )
        logger.info("Downloaded rice dataset to: %s", path)

        RICE_RAW_DIR.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(str(path), str(RICE_RAW_DIR), dirs_exist_ok=True)
        logger.info("Copied rice dataset to: %s", RICE_RAW_DIR)
    except Exception as e:
        logger.error("Rice download failed: %s", e)


def prepare_plantvillage_data():
    PREPARED_DIR.mkdir(parents=True, exist_ok=True)

    plantvillage_dir = RAW_DIR
    if (RAW_DIR / "PlantVillage").exists():
        plantvillage_dir = RAW_DIR / "PlantVillage"
    elif (RAW_DIR / "plantvillage").exists():
        plantvillage_dir = RAW_DIR / "plantvillage"

    all_classes = list(plantvillage_dir.glob("*")) if plantvillage_dir.exists() else []
    logger.info("Found %d PlantVillage class folders", len(all_classes))
    for c in sorted(all_classes):
        if c.is_dir():
            img_count = len(list(c.glob("*.jpg")))
            if img_count > 0:
                logger.info("  %s (%d images)", c.name, img_count)

    total_images = 0
    total_copied = 0

    for crop_name, class_mapping in PLANTVILLAGE_TO_OURS.items():
        if crop_name == "Rice":
            continue
        logger.info("Processing crop: %s", crop_name)

        crop_images = []
        for pv_class, our_class in class_mapping.items():
            pv_dir = plantvillage_dir / pv_class
            if not pv_dir.exists():
                continue
            for img in pv_dir.glob("*.jpg"):
                crop_images.append((img, our_class))

        if not crop_images:
            logger.warning("  No images found for %s, skipping", crop_name)
            continue

        random.shuffle(crop_images)
        n = len(crop_images)
        train_end = int(n * TRAIN_RATIO)
        val_end = int(n * (TRAIN_RATIO + VAL_RATIO))

        splits = {
            "train": crop_images[:train_end],
            "val": crop_images[train_end:val_end],
            "test": crop_images[val_end:],
        }

        for split_name, split_data in splits.items():
            for img_path, class_name in split_data:
                dest_dir = PREPARED_DIR / crop_name / split_name / class_name
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_file = dest_dir / img_path.name
                if not dest_file.exists():
                    shutil.copy2(str(img_path), str(dest_file))
                    total_copied += 1
            total_images += len(split_data)

        class_counts = {}
        for _, cls in crop_images:
            class_counts[cls] = class_counts.get(cls, 0) + 1
        logger.info(
            "  %s: %d images across %d classes", crop_name, len(crop_images), len(class_counts)
        )
        for cls, count in sorted(class_counts.items()):
            logger.info("    %s: %d", cls, count)

    logger.info("PlantVillage preparation: %d images, %d copied", total_images, total_copied)


def prepare_rice_data():
    PREPARED_DIR.mkdir(parents=True, exist_ok=True)

    rice_dir = None
    for candidate in [
        RICE_RAW_DIR / "rice_leaf_diseases_dataset",
        RICE_RAW_DIR / "versions" / "1" / "rice_leaf_diseases_dataset",
        RICE_RAW_DIR / "versions" / "1",
        RICE_RAW_DIR / "1" / "rice_leaf_diseases_dataset",
        RICE_RAW_DIR,
    ]:
        if candidate.exists() and any(candidate.iterdir()):
            rice_dir = candidate
            break
    if rice_dir is None:
        for p in RICE_RAW_DIR.rglob("Bacterial leaf blight"):
            rice_dir = p.parent
            break

    if rice_dir is None or not rice_dir.exists():
        logger.warning("Rice dataset not found at %s", RICE_RAW_DIR)
        return

    logger.info("Preparing rice data from: %s", rice_dir)

    crop_images = []
    for pv_class, our_class in RICE_MAPPING.items():
        class_dir = rice_dir / pv_class
        if not class_dir.exists():
            logger.warning("  Rice class folder not found: %s", pv_class)
            continue
        for ext in ["*.jpg", "*.JPG", "*.jpeg", "*.png"]:
            for img in class_dir.glob(ext):
                crop_images.append((img, our_class))

    if not crop_images:
        logger.warning("No rice images found")
        return

    random.shuffle(crop_images)
    n = len(crop_images)
    train_end = int(n * TRAIN_RATIO)
    val_end = int(n * (TRAIN_RATIO + VAL_RATIO))

    splits = {
        "train": crop_images[:train_end],
        "val": crop_images[train_end:val_end],
        "test": crop_images[val_end:],
    }

    total_copied = 0
    for split_name, split_data in splits.items():
        for img_path, class_name in split_data:
            dest_dir = PREPARED_DIR / "Rice" / split_name / class_name
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / img_path.name
            if not dest_file.exists():
                shutil.copy2(str(img_path), str(dest_file))
                total_copied += 1

    class_counts = {}
    for _, cls in crop_images:
        class_counts[cls] = class_counts.get(cls, 0) + 1
    logger.info("  Rice: %d images across %d classes", len(crop_images), len(class_counts))
    for cls, count in sorted(class_counts.items()):
        logger.info("    %s: %d", cls, count)
    logger.info("Rice preparation complete: %d images, %d copied", len(crop_images), total_copied)


if __name__ == "__main__":
    download_plantvillage()
    download_rice()
    prepare_plantvillage_data()
    prepare_rice_data()
    logger.info("All datasets prepared in: %s", PREPARED_DIR)
