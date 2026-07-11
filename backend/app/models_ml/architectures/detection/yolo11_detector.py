import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class Detection:
    def __init__(
        self,
        bbox: tuple[int, int, int, int],
        class_label: str,
        confidence: float,
        class_id: int = 0,
    ):
        self.bbox = bbox
        self.class_label = class_label
        self.confidence = confidence
        self.class_id = class_id

    @property
    def area(self) -> int:
        x1, y1, x2, y2 = self.bbox
        return max(0, x2 - x1) * max(0, y2 - y1)

    def to_dict(self) -> dict:
        return {
            "bbox": list(self.bbox),
            "class_label": self.class_label,
            "confidence": self.confidence,
            "area_pixels": self.area,
        }


class YOLODetector:
    DEFAULT_CLASSES = [
        "healthy_leaf",
        "necrotic_lesion",
        "brown_spot",
        "chlorotic_spot",
        "bacterial_lesion",
    ]

    def __init__(
        self,
        model_path: Path | str | None = None,
        class_names: list[str] | None = None,
        conf_threshold: float = 0.25,
    ):
        self.model_path = Path(model_path) if model_path else None
        self.class_names = class_names or self.DEFAULT_CLASSES
        self.conf_threshold = conf_threshold
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return
        if self.model_path is None or not self.model_path.exists():
            raise FileNotFoundError(f"YOLO model not found: {self.model_path}")
        try:
            from ultralytics import YOLO

            self._model = YOLO(str(self.model_path))
            logger.info("Loaded YOLO model from %s", self.model_path)
        except ImportError as err:
            raise ImportError(
                "ultralytics is required for YOLO detection. Install with: pip install ultralytics"
            ) from err

    def detect(self, image: np.ndarray) -> list[Detection]:
        if self.model_path is None or not self.model_path.exists():
            return []

        try:
            self._load_model()
            results = self._model(image, conf=self.conf_threshold, verbose=False)
        except Exception:
            logger.warning("YOLO detection failed", exc_info=True)
            return []

        detections: list[Detection] = []
        for result in results:
            if result.boxes is None:
                continue
            boxes = result.boxes
            for i in range(len(boxes)):
                xyxy = boxes.xyxy[i].cpu().numpy().astype(int)
                conf = float(boxes.conf[i])
                cls_id = int(boxes.cls[i])
                x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
                label = (
                    self.class_names[cls_id]
                    if cls_id < len(self.class_names)
                    else f"class_{cls_id}"
                )
                detections.append(
                    Detection(
                        bbox=(x1, y1, x2, y2), class_label=label, confidence=conf, class_id=cls_id
                    )
                )

        logger.info("YOLO detected %d objects", len(detections))
        return detections

    def detect_lesions(self, image: np.ndarray) -> list[Detection]:
        all_detections = self.detect(image)
        return [d for d in all_detections if d.class_label != "healthy_leaf"]

    def get_detection_summary(self, detections: list[Detection]) -> dict:
        total_area = sum(d.area for d in detections)
        lesion_count = len([d for d in detections if d.class_label != "healthy_leaf"])
        lesion_area = sum(d.area for d in detections if d.class_label != "healthy_leaf")
        return {
            "total_detections": len(detections),
            "lesion_count": lesion_count,
            "total_detection_area": total_area,
            "lesion_area": lesion_area,
            "lesions": [d.to_dict() for d in detections],
        }

    @classmethod
    def train(
        cls,
        data_yaml: str,
        model_size: str = "n",
        epochs: int = 100,
        imgsz: int = 640,
        device: str = "cpu",
    ):
        try:
            from ultralytics import YOLO

            model = YOLO(f"yolo11{model_size}.pt")
            results = model.train(
                data=data_yaml,
                epochs=epochs,
                imgsz=imgsz,
                device=device,
                project="runs/detect",
                name="agriai",
            )
            return results
        except ImportError as err:
            raise ImportError("ultralytics is required. Install with: pip install ultralytics") from err

    @classmethod
    def export_onnx(cls, model_path: Path, output_path: Path, imgsz: int = 640):
        try:
            from ultralytics import YOLO

            model = YOLO(str(model_path))
            model.export(format="onnx", imgsz=imgsz)
            logger.info("Exported YOLO to ONNX: %s", output_path)
        except ImportError as err:
            raise ImportError("ultralytics is required. Install with: pip install ultralytics") from err
