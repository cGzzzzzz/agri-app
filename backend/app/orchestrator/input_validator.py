from pathlib import Path

from app.orchestrator.input_types import OrchestratorInput


class ValidationError(Exception):
    pass


class InputValidator:
    ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    SUPPORTED_CROPS = {
        "rice",
        "tomato",
        "potato",
        "pepper",
        "wheat",
        "maize",
        "cotton",
        "sugarcane",
        "banana",
    }

    def validate(
        self,
        state: dict,
        user=None,
        image_path: str = "",
        image_id: int | None = None,
        farm_id: int | None = None,
        crop_id: int | None = None,
        crop_override: str | None = None,
        include_xai_heatmap: bool = False,
    ) -> OrchestratorInput:
        if user is None:
            user = state.get("user")
        if not user:
            raise ValidationError("User is required")

        if not hasattr(user, "id") or not user.id:
            raise ValidationError("User must have a valid id")

        if not hasattr(user, "is_active") or not user.is_active:
            raise ValidationError("User account is inactive")

        if not image_path:
            raise ValidationError("Image path is required")

        path = Path(image_path)
        if not path.exists():
            raise ValidationError(f"Image file does not exist: {image_path}")

        if not path.is_file():
            raise ValidationError(f"Path is not a file: {image_path}")

        extension = path.suffix.lower()
        if extension not in self.ALLOWED_IMAGE_EXTENSIONS:
            raise ValidationError(
                f"Unsupported image format: {extension}. "
                f"Allowed: {', '.join(self.ALLOWED_IMAGE_EXTENSIONS)}"
            )

        from app.config import get_settings

        settings = get_settings()
        max_bytes = int(settings.image_max_size_mb * 1024 * 1024)
        size_bytes = path.stat().st_size
        if size_bytes > max_bytes:
            raise ValidationError(
                f"Image too large: {size_bytes / (1024 * 1024):.1f}MB. "
                f"Maximum: {settings.image_max_size_mb}MB"
            )

        if crop_override:
            normalized = crop_override.strip().lower()
            if normalized not in self.SUPPORTED_CROPS:
                raise ValidationError(
                    f"Unsupported crop: {crop_override}. "
                    f"Supported: {', '.join(sorted(self.SUPPORTED_CROPS))}"
                )
            crop_override = normalized.capitalize()

        return OrchestratorInput(
            user_id=user.id,
            user_language=getattr(user, "language", "en") or "en",
            image_path=image_path,
            image_id=image_id,
            farm_id=farm_id,
            crop_id=crop_id,
            crop_override=crop_override,
            include_xai_heatmap=include_xai_heatmap,
        )
