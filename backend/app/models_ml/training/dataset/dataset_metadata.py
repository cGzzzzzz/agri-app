import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.models_ml.training.dataset.dataset_version import DatasetVersion


@dataclass
class DatasetMetadata:
    name: str
    crop: str
    task: str
    description: str = ""
    class_names: list[str] = field(default_factory=list)
    total_samples: int = 0
    versions: list[DatasetVersion] = field(default_factory=list)
    created_at: str = ""
    tags: list[str] = field(default_factory=list)
    augmentation: list[str] = field(default_factory=list)
    license: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @property
    def latest_version(self) -> DatasetVersion | None:
        return self.versions[-1] if self.versions else None

    def add_version(self, version: DatasetVersion) -> None:
        existing = [v for v in self.versions if v.version == version.version]
        if existing:
            self.versions.remove(existing[0])
        self.versions.append(version)
        self.versions.sort(key=lambda v: v.version)
        self.total_samples = sum(v.total_samples for v in self.versions)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "crop": self.crop,
            "task": self.task,
            "description": self.description,
            "class_names": self.class_names,
            "total_samples": self.total_samples,
            "versions": [v.to_dict() for v in self.versions],
            "created_at": self.created_at,
            "tags": self.tags,
            "augmentation": self.augmentation,
            "license": self.license,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "DatasetMetadata":
        versions = [DatasetVersion.from_dict(v) for v in data.get("versions", [])]
        return cls(
            name=data["name"],
            crop=data.get("crop", ""),
            task=data.get("task", ""),
            description=data.get("description", ""),
            class_names=data.get("class_names", []),
            total_samples=data.get("total_samples", 0),
            versions=versions,
            created_at=data.get("created_at", ""),
            tags=data.get("tags", []),
            augmentation=data.get("augmentation", []),
            license=data.get("license", ""),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "DatasetMetadata":
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_json_file(cls, path: str) -> "DatasetMetadata":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
