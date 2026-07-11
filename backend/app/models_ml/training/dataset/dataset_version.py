from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class DatasetVersion:
    version: str
    split_counts: dict[str, int] = field(default_factory=dict)
    created_at: str = ""
    description: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat()

    @property
    def total_samples(self) -> int:
        return sum(self.split_counts.values())

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "split_counts": self.split_counts,
            "created_at": self.created_at,
            "description": self.description,
            "total_samples": self.total_samples,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DatasetVersion":
        return cls(
            version=data["version"],
            split_counts=data.get("split_counts", {}),
            created_at=data.get("created_at", ""),
            description=data.get("description", ""),
        )
