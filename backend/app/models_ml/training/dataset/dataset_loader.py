import logging
from collections.abc import Iterator
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

try:
    from PIL import Image
except ImportError:
    Image = None


class DatasetLoader:
    def __init__(
        self,
        data_dir: Path | str,
        class_names: list[str] | None = None,
        image_size: tuple[int, int] = (224, 224),
        batch_size: int = 32,
        shuffle: bool = True,
    ):
        self.data_dir = Path(data_dir)
        self.class_names = class_names or []
        self.image_size = image_size
        self.batch_size = batch_size
        self.shuffle = shuffle
        self._samples: list[tuple[Path, int]] = []
        self._build_index()

    def _build_index(self) -> None:
        if not self.data_dir.exists():
            logger.warning("Data directory does not exist: %s", self.data_dir)
            return
        for class_idx, class_name in enumerate(self.class_names):
            class_dir = self.data_dir / class_name
            if not class_dir.exists():
                continue
            for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp"):
                for img_path in class_dir.glob(ext):
                    self._samples.append((img_path, class_idx))

        if self.shuffle and len(self._samples) > 1:
            indices = np.random.permutation(len(self._samples))
            self._samples = [self._samples[i] for i in indices]

    def __len__(self) -> int:
        return max(1, (len(self._samples) + self.batch_size - 1) // self.batch_size)

    def __iter__(self) -> Iterator[tuple[np.ndarray, np.ndarray]]:
        for i in range(0, len(self._samples), self.batch_size):
            batch = self._samples[i : i + self.batch_size]
            images = []
            labels = []
            for img_path, label in batch:
                try:
                    img = self._load_image(img_path)
                    if img is not None:
                        images.append(img)
                        labels.append(label)
                except Exception:
                    logger.warning("Failed to load image: %s", img_path)
                    continue

            if not images:
                continue

            images_arr = np.stack(images, axis=0)
            labels_arr = np.array(labels, dtype=np.int64)
            yield images_arr, labels_arr

    def _load_image(self, path: Path) -> np.ndarray | None:
        if Image is None:
            raise ImportError(
                "Pillow is required for loading images. Install with: pip install Pillow"
            )

        img = Image.open(path).convert("RGB")
        img = img.resize(self.image_size, Image.BILINEAR)
        arr = np.array(img, dtype=np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        arr = (arr - mean) / std
        return arr.transpose(2, 0, 1)

    def iter_samples(self) -> Iterator[tuple[np.ndarray, int]]:
        for img_path, label in self._samples:
            try:
                img = self._load_image(img_path)
                if img is not None:
                    yield img, label
            except Exception:
                continue

    def to_pytorch_dataset(self):
        try:
            import torch
            from torch.utils.data import DataLoader, Dataset

            class _TorchDataset(Dataset):
                def __init__(self, loader: "DatasetLoader"):
                    self._samples = []
                    for img_path, label in loader._samples:
                        self._samples.append((img_path, label))
                    self._loader = loader

                def __len__(self):
                    return len(self._samples)

                def __getitem__(self, idx):
                    path, label = self._samples[idx]
                    arr = self._loader._load_image(path)
                    if arr is None:
                        arr = np.zeros((3, *self._loader.image_size), dtype=np.float32)
                        label = 0
                    return torch.from_numpy(arr), label

            dataset = _TorchDataset(self)
            return DataLoader(
                dataset,
                batch_size=self.batch_size,
                shuffle=self.shuffle,
                num_workers=0,
                drop_last=False,
            )
        except ImportError:
            logger.warning("PyTorch not available, returning None for PyTorch DataLoader")
            return None

    @property
    def num_classes(self) -> int:
        return len(self.class_names)

    @property
    def num_samples(self) -> int:
        return len(self._samples)

    def class_distribution(self) -> dict[str, int]:
        dist = {name: 0 for name in self.class_names}
        for _, label in self._samples:
            if 0 <= label < len(self.class_names):
                dist[self.class_names[label]] += 1
        return dist

    def split(
        self, train_ratio: float = 0.8, val_ratio: float = 0.1
    ) -> tuple["DatasetLoader", "DatasetLoader", "DatasetLoader"]:
        n = len(self._samples)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))

        train_data = self._samples[:train_end]
        val_data = self._samples[train_end:val_end]
        test_data = self._samples[val_end:]

        train_loader = DatasetLoader(
            self.data_dir, self.class_names, self.image_size, self.batch_size, shuffle=True
        )
        val_loader = DatasetLoader(
            self.data_dir, self.class_names, self.image_size, self.batch_size, shuffle=False
        )
        test_loader = DatasetLoader(
            self.data_dir, self.class_names, self.image_size, self.batch_size, shuffle=False
        )

        train_loader._samples = train_data
        val_loader._samples = val_data
        test_loader._samples = test_data

        return train_loader, val_loader, test_loader
