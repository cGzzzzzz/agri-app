from pathlib import Path

from app.models_ml.training.dataset.dataset_metadata import DatasetMetadata


class DatasetRegistry:
    def __init__(self, registry_dir: Path | str = "datasets"):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self._datasets: dict[str, DatasetMetadata] = {}

    def register(self, name: str, metadata: DatasetMetadata) -> None:
        self._datasets[name] = metadata
        meta_path = self.registry_dir / f"{name}.json"
        meta_path.write_text(metadata.to_json(), encoding="utf-8")

    def get(self, name: str) -> DatasetMetadata | None:
        if name in self._datasets:
            return self._datasets[name]
        meta_path = self.registry_dir / f"{name}.json"
        if meta_path.exists():
            return DatasetMetadata.from_json(meta_path.read_text(encoding="utf-8"))
        return None

    def list_datasets(self) -> list[DatasetMetadata]:
        results = []
        for json_path in self.registry_dir.glob("*.json"):
            try:
                meta = DatasetMetadata.from_json(json_path.read_text(encoding="utf-8"))
                results.append(meta)
            except Exception:
                continue
        return results

    def delete(self, name: str) -> bool:
        meta_path = self.registry_dir / f"{name}.json"
        if meta_path.exists():
            meta_path.unlink()
            self._datasets.pop(name, None)
            return True
        return False

    def list_by_crop(self, crop: str) -> list[DatasetMetadata]:
        return [d for d in self.list_datasets() if d.crop.lower() == crop.lower()]

    def list_by_task(self, task: str) -> list[DatasetMetadata]:
        return [d for d in self.list_datasets() if d.task == task]
