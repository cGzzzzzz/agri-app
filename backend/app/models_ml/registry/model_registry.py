import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    name: str
    version: str
    crop: str
    framework: str
    task: str
    classes: list[str]
    input_shape: list[int]
    preprocessing: str
    artifact_path: str
    description: str = ""
    metrics: dict[str, float] = field(default_factory=dict)
    created_at: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "crop": self.crop,
            "framework": self.framework,
            "task": self.task,
            "classes": self.classes,
            "input_shape": self.input_shape,
            "preprocessing": self.preprocessing,
            "artifact_path": self.artifact_path,
            "description": self.description,
            "metrics": self.metrics,
            "created_at": self.created_at,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ModelMetadata":
        return cls(
            name=data["name"],
            version=data["version"],
            crop=data.get("crop", ""),
            framework=data.get("framework", "onnx"),
            task=data["task"],
            classes=data.get("classes", []),
            input_shape=data.get("input_shape", [1, 3, 224, 224]),
            preprocessing=data.get("preprocessing", "imagenet_normalize"),
            artifact_path=data["artifact_path"],
            description=data.get("description", ""),
            metrics=data.get("metrics", {}),
            created_at=data.get("created_at", ""),
            tags=data.get("tags", []),
        )


class ModelSession(Protocol):
    def run(self, input_name: str, inputs: Any) -> Any: ...


@dataclass
class LoadedModel:
    metadata: ModelMetadata
    session: Any


class ModelRegistry:
    def __init__(self, artifacts_dir: Path | str = "artifacts"):
        self.artifacts_dir = Path(artifacts_dir)
        self._metadata: dict[str, ModelMetadata] = {}
        self._loaded: dict[str, LoadedModel] = {}
        self._version_index: dict[str, list[str]] = {}

    def discover(self) -> int:
        count = 0
        if not self.artifacts_dir.exists():
            logger.info("Artifacts directory does not exist: %s", self.artifacts_dir)
            return count

        for metadata_path in self.artifacts_dir.rglob("metadata.json"):
            try:
                data = json.loads(metadata_path.read_text(encoding="utf-8"))
                meta = ModelMetadata.from_dict(data)
                self._metadata[meta.name] = meta

                version_list = self._version_index.setdefault(meta.name, [])
                if meta.version not in version_list:
                    version_list.append(meta.version)
                version_list.sort()

                count += 1
                logger.info("Discovered model: %s v%s (%s)", meta.name, meta.version, meta.task)
            except Exception:
                logger.warning("Failed to load metadata from %s", metadata_path, exc_info=True)

        logger.info("Model discovery complete: %d models found", count)
        return count

    def register(
        self,
        name: str,
        version: str,
        metadata: ModelMetadata,
        artifact_path: Path | str | None = None,
    ) -> None:
        if artifact_path:
            metadata.artifact_path = str(artifact_path)
        self._metadata[name] = metadata

        version_list = self._version_index.setdefault(name, [])
        if version not in version_list:
            version_list.append(version)
            version_list.sort()

        logger.info("Registered model: %s v%s", name, version)

    def get_metadata(self, name: str) -> ModelMetadata | None:
        return self._metadata.get(name)

    def latest_version(self, name: str) -> str | None:
        versions = self._version_index.get(name, [])
        return versions[-1] if versions else None

    def resolve(self, task: str, crop: str = "") -> ModelMetadata | None:
        candidates = []
        for meta in self._metadata.values():
            if meta.task != task:
                continue
            if crop and meta.crop and meta.crop.lower() != crop.lower():
                continue
            candidates.append(meta)

        if not candidates:
            return None

        def sort_key(m: ModelMetadata) -> tuple:
            crop_match = 0 if (crop and m.crop.lower() == crop.lower()) else 1
            version_parts = [int(p) for p in m.version.split(".")]
            return (crop_match, version_parts)

        candidates.sort(key=sort_key, reverse=True)
        return candidates[0]

    def load(self, name: str) -> LoadedModel | None:
        if name in self._loaded:
            return self._loaded[name]

        meta = self._metadata.get(name)
        if meta is None:
            logger.warning("Model not found in registry: %s", name)
            return None

        artifact_path = Path(meta.artifact_path)
        if not artifact_path.exists():
            logger.warning("Artifact file missing for %s: %s", name, artifact_path)
            return None

        try:
            import onnxruntime as ort

            sess_options = ort.SessionOptions()
            sess_options.inter_op_num_threads = 4
            sess_options.intra_op_num_threads = 4
            session = ort.InferenceSession(str(artifact_path), sess_options)
            loaded = LoadedModel(metadata=meta, session=session)
            self._loaded[name] = loaded
            logger.info("Loaded model: %s from %s", name, artifact_path)
            return loaded
        except Exception:
            logger.error("Failed to load ONNX model %s from %s", name, artifact_path, exc_info=True)
            return None

    def load_latest(self, task: str, crop: str = "") -> LoadedModel | None:
        meta = self.resolve(task, crop)
        if meta is None:
            return None
        return self.load(meta.name)

    def list_models(self) -> list[ModelMetadata]:
        return list(self._metadata.values())

    def list_by_task(self, task: str) -> list[ModelMetadata]:
        return [m for m in self._metadata.values() if m.task == task]

    def list_by_crop(self, crop: str) -> list[ModelMetadata]:
        return [m for m in self._metadata.values() if m.crop.lower() == crop.lower()]

    def has_model(self, task: str, crop: str = "") -> bool:
        return self.resolve(task, crop) is not None

    def unload(self, name: str) -> None:
        self._loaded.pop(name, None)

    def unload_all(self) -> None:
        self._loaded.clear()

    def model_info(self, name: str) -> dict | None:
        meta = self._metadata.get(name)
        return meta.to_dict() if meta else None

    def all_model_cards(self) -> list[dict]:
        cards = []
        for meta in self._metadata.values():
            cards.append({
                "name": meta.name,
                "task": meta.task,
                "version": meta.version,
                "crop": meta.crop,
                "framework": meta.framework,
                "classes": meta.classes,
                "status": "trained",
                "metrics": meta.metrics,
            })
        return cards
