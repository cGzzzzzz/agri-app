import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

from app.vision.types import VisionFeatures, VisionInput

logger = logging.getLogger(__name__)


@dataclass
class ProcessedImage:
    image_path: Path
    pixels: np.ndarray
    tensor: np.ndarray
    original_size: tuple[int, int]
    image_format: str
    quality_warnings: list[str]
    features: VisionFeatures


class RealImagePreprocessor:
    IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

    def __init__(self, target_size: tuple[int, int] = (224, 224)):
        self.target_size = target_size

    def process(self, image_path: Path, crop_hint: str | None = None) -> ProcessedImage:
        warnings: list[str] = []
        extension = image_path.suffix.lower()

        if extension not in self.ALLOWED_EXTENSIONS:
            warnings.append(f"Unsupported extension: {extension}")

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        size_bytes = image_path.stat().st_size
        if size_bytes == 0:
            raise ValueError(f"Image file is empty: {image_path}")

        if size_bytes < 128:
            warnings.append("Image is very small; confidence should be treated as low.")

        img = Image.open(image_path)
        original_size = img.size

        if img.mode != "RGB":
            warnings.append(f"Converted from {img.mode} to RGB")
            img = img.convert("RGB")

        blur_score = self._detect_blur(img)
        if blur_score < 50.0:
            warnings.append(f"Image may be blurry (Laplacian variance: {blur_score:.1f})")

        brightness = self._detect_brightness(img)
        if brightness < 30:
            warnings.append("Image appears very dark")
        elif brightness > 225:
            warnings.append("Image appears very bright/overexposed")

        img_resized = img.resize(self.target_size, Image.BILINEAR)
        pixels = np.array(img_resized, dtype=np.float32) / 255.0

        tensor = (pixels - self.IMAGENET_MEAN) / self.IMAGENET_STD
        tensor = tensor.transpose(2, 0, 1)
        tensor = tensor[np.newaxis, ...]

        image_sig = self._detect_format(image_path)
        tokens = [t for t in image_path.stem.lower().replace("-", "_").split("_") if t]
        if crop_hint:
            tokens.append(crop_hint.lower())

        features = VisionFeatures(
            filename=image_path.name,
            extension=extension,
            size_bytes=size_bytes,
            image_signature=image_sig,
            quality_warnings=warnings,
            tokens=tokens,
        )

        return ProcessedImage(
            image_path=image_path,
            pixels=pixels,
            tensor=tensor,
            original_size=original_size,
            image_format=image_sig,
            quality_warnings=warnings,
            features=features,
        )

    def _detect_blur(self, img: Image.Image) -> float:
        try:
            import cv2

            arr = np.array(img.convert("L"))
            return float(cv2.Laplacian(arr, cv2.CV_64F).var())
        except ImportError:
            arr = np.array(img.convert("L"), dtype=np.float64)
            gy, gx = np.gradient(arr)
            gxx = gx * gx
            gyy = gy * gy
            return float(np.mean(gxx + gyy))

    def _detect_brightness(self, img: Image.Image) -> float:
        arr = np.array(img.convert("L"), dtype=np.float32)
        return float(np.mean(arr))

    def _detect_format(self, path: Path) -> str:
        if not path.exists():
            return "missing"
        header = path.read_bytes()[:12]
        if header.startswith(b"\xff\xd8\xff"):
            return "jpeg"
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        if header.startswith(b"RIFF") and b"WEBP" in header:
            return "webp"
        return "unknown"
