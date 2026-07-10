from pathlib import Path

from app.vision.types import VisionFeatures, VisionInput


class ImagePreprocessor:
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}

    def inspect(self, vision_input: VisionInput) -> VisionFeatures:
        path = vision_input.image_path
        extension = path.suffix.lower()
        size_bytes = path.stat().st_size if path.exists() else 0
        warnings: list[str] = []

        if extension not in self.allowed_extensions:
            warnings.append("Unsupported extension for trained model path; baseline still runs.")
        if size_bytes == 0:
            warnings.append("Image file is empty or unavailable.")
        elif size_bytes < 128:
            warnings.append("Image is very small; confidence should be treated as low.")

        signature = self._signature(path)
        tokens = [token for token in path.stem.lower().replace("-", "_").split("_") if token]
        if vision_input.crop_hint:
            tokens.append(vision_input.crop_hint.lower())

        return VisionFeatures(
            filename=path.name,
            extension=extension,
            size_bytes=size_bytes,
            image_signature=signature,
            quality_warnings=warnings,
            tokens=tokens,
        )

    def _signature(self, path: Path) -> str:
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
