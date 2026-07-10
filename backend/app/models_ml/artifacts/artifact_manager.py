import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from app.models_ml.registry.model_registry import ModelMetadata

logger = logging.getLogger(__name__)


class ArtifactManager:
    def __init__(self, base_dir: Path | str = "artifacts"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _model_dir(self, model_name: str, version: str) -> Path:
        return self.base_dir / model_name / version

    def save(
        self,
        model_name: str,
        version: str,
        model_bytes: bytes,
        metadata: ModelMetadata,
        extra_files: dict[str, bytes] | None = None,
    ) -> Path:
        target = self._model_dir(model_name, version)
        target.mkdir(parents=True, exist_ok=True)

        ext = ".onnx"
        model_path = target / f"model{ext}"
        model_path.write_bytes(model_bytes)
        logger.info("Saved model artifact: %s", model_path)

        metadata.artifact_path = str(model_path)
        metadata.created_at = datetime.now(timezone.utc).isoformat()
        meta_path = target / "metadata.json"
        meta_path.write_text(json.dumps(metadata.to_dict(), indent=2), encoding="utf-8")
        logger.info("Saved metadata: %s", meta_path)

        if extra_files:
            for fname, fbytes in extra_files.items():
                extra_path = target / fname
                extra_path.write_bytes(fbytes)

        return model_path

    def load_model_bytes(self, model_name: str, version: str) -> bytes | None:
        target = self._model_dir(model_name, version)
        model_path = target / "model.onnx"
        if not model_path.exists():
            logger.warning("Model artifact not found: %s", model_path)
            return None
        return model_path.read_bytes()

    def load_metadata(self, model_name: str, version: str) -> ModelMetadata | None:
        target = self._model_dir(model_name, version)
        meta_path = target / "metadata.json"
        if not meta_path.exists():
            return None
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            return ModelMetadata.from_dict(data)
        except Exception:
            logger.warning("Failed to load metadata from %s", meta_path, exc_info=True)
            return None

    def list_versions(self, model_name: str) -> list[str]:
        model_dir = self.base_dir / model_name
        if not model_dir.exists():
            return []
        versions = []
        for item in model_dir.iterdir():
            if item.is_dir() and (item / "metadata.json").exists():
                versions.append(item.name)
        versions.sort()
        return versions

    def delete_version(self, model_name: str, version: str) -> bool:
        target = self._model_dir(model_name, version)
        if not target.exists():
            return False
        shutil.rmtree(target)
        logger.info("Deleted artifact: %s v%s", model_name, version)
        return True

    def delete_model(self, model_name: str) -> bool:
        model_dir = self.base_dir / model_name
        if not model_dir.exists():
            return False
        shutil.rmtree(model_dir)
        logger.info("Deleted all versions of model: %s", model_name)
        return True

    def save_checkpoint(
        self,
        model_name: str,
        version: str,
        checkpoint_name: str,
        model_bytes: bytes,
    ) -> Path:
        target = self._model_dir(model_name, version) / "checkpoints"
        target.mkdir(parents=True, exist_ok=True)
        ckpt_path = target / f"{checkpoint_name}.onnx"
        ckpt_path.write_bytes(model_bytes)
        return ckpt_path

    def list_checkpoints(self, model_name: str, version: str) -> list[str]:
        ckpt_dir = self._model_dir(model_name, version) / "checkpoints"
        if not ckpt_dir.exists():
            return []
        return [p.stem for p in ckpt_dir.glob("*.onnx")]

    def save_eval_report(
        self,
        model_name: str,
        version: str,
        report: dict,
    ) -> Path:
        target = self._model_dir(model_name, version)
        target.mkdir(parents=True, exist_ok=True)
        report_path = target / "eval_report.json"
        report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        return report_path

    def load_eval_report(self, model_name: str, version: str) -> dict | None:
        target = self._model_dir(model_name, version)
        report_path = target / "eval_report.json"
        if not report_path.exists():
            return None
        try:
            return json.loads(report_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def model_exists(self, model_name: str, version: str) -> bool:
        return (self._model_dir(model_name, version) / "model.onnx").exists()
