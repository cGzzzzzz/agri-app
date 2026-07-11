import base64
import io
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class HeatmapRenderer:
    def overlay_heatmap(
        self,
        image: np.ndarray,
        heatmap: np.ndarray,
        alpha: float = 0.4,
        colormap: int = cv2.COLORMAP_JET,
    ) -> np.ndarray:
        if image.ndim == 3 and image.shape[2] == 3:
            img_uint8 = image.copy()
            if img_uint8.dtype != np.uint8:
                img_uint8 = (np.clip(img_uint8, 0, 1) * 255).astype(np.uint8)
        else:
            img_uint8 = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB) if image.ndim == 2 else image

        heatmap_resized = cv2.resize(heatmap, (img_uint8.shape[1], img_uint8.shape[0]))
        heatmap_uint8 = (np.clip(heatmap_resized, 0, 1) * 255).astype(np.uint8)
        heatmap_colored = cv2.applyColorMap(heatmap_uint8, colormap)
        heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)

        overlay = (1 - alpha) * img_uint8.astype(np.float32) + alpha * heatmap_colored.astype(
            np.float32
        )
        return np.clip(overlay, 0, 255).astype(np.uint8)

    def draw_detections(
        self,
        image: np.ndarray,
        detections: list,
        colors: dict | None = None,
    ) -> np.ndarray:
        if colors is None:
            colors = {
                "necrotic_lesion": (255, 0, 0),
                "brown_spot": (180, 100, 0),
                "chlorotic_spot": (255, 255, 0),
                "bacterial_lesion": (200, 0, 200),
                "healthy_leaf": (0, 200, 0),
            }
        default_color = (255, 255, 255)

        img = image.copy()
        if img.dtype != np.uint8:
            img = (np.clip(img, 0, 1) * 255).astype(np.uint8)

        for det in detections:
            if hasattr(det, "bbox"):
                x1, y1, x2, y2 = det.bbox
                label = det.class_label
                conf = det.confidence
            elif isinstance(det, dict):
                bbox = det.get("bbox", [0, 0, 0, 0])
                x1, y1, x2, y2 = bbox
                label = det.get("class_label", "unknown")
                conf = det.get("confidence", 0.0)
            else:
                continue

            color = colors.get(label, default_color)
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

            text = f"{label}: {conf:.0%}"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(img, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
            cv2.putText(
                img, text, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
            )

        return img

    def render_full_xai_overlay(
        self,
        image: np.ndarray,
        heatmap: np.ndarray | None = None,
        detections: list | None = None,
    ) -> str:
        result = image.copy()
        if result.dtype != np.uint8:
            result = (np.clip(result, 0, 1) * 255).astype(np.uint8)

        if heatmap is not None:
            result = self.overlay_heatmap(result, heatmap, alpha=0.35)

        if detections:
            result = self.draw_detections(result, detections)

        return self._to_base64(result)

    def _to_base64(self, image: np.ndarray) -> str:
        try:
            img = __import__("PIL").Image.fromarray(image)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            return ""
