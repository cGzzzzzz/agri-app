import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class DetectionDataset:
    def __init__(self, data_dir: Path | str, img_size: int = 640):
        self.data_dir = Path(data_dir)
        self.img_size = img_size
        self._samples: list[tuple[Path, Path]] = []
        self._class_names: list[str] = []
        self._build_index()

    def _build_index(self) -> None:
        images_dir = self.data_dir / "images"
        labels_dir = self.data_dir / "labels"

        if not images_dir.exists():
            logger.warning("Images directory not found: %s", images_dir)
            return

        for split in ["train", "val", "test"]:
            split_images = images_dir / split
            split_labels = labels_dir / split
            if not split_images.exists():
                continue
            for img_path in sorted(split_images.glob("*")):
                if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                    continue
                label_path = split_labels / f"{img_path.stem}.txt"
                self._samples.append((img_path, label_path))

        classes_file = self.data_dir / "classes.txt"
        if classes_file.exists():
            self._class_names = [
                line.strip() for line in classes_file.read_text().splitlines() if line.strip()
            ]

    @property
    def num_samples(self) -> int:
        return len(self._samples)

    @property
    def class_names(self) -> list[str]:
        return self._class_names

    def load_sample(self, index: int) -> tuple[np.ndarray, list[dict]]:
        img_path, label_path = self._samples[index]
        image = np.array(__import__("PIL").Image.open(img_path).convert("RGB"))

        annotations = []
        if label_path.exists():
            for line in label_path.read_text().splitlines():
                parts = line.strip().split()
                if len(parts) >= 5:
                    class_id = int(parts[0])
                    x_center, y_center, w, h = map(float, parts[1:5])
                    annotations.append(
                        {
                            "class_id": class_id,
                            "x_center": x_center,
                            "y_center": y_center,
                            "width": w,
                            "height": h,
                        }
                    )

        return image, annotations

    def get_data_yaml_content(self) -> str:
        lines = [
            f"path: {self.data_dir}",
            "train: images/train",
            "val: images/val",
            f"nc: {len(self._class_names)}",
            f"names: {self._class_names}",
        ]
        return "\n".join(lines)
