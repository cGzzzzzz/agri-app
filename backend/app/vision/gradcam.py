import base64
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class GradCAMGenerator:
    def __init__(self, target_layer_name: str | None = None):
        self.target_layer_name = target_layer_name

    def generate_heatmap(
        self,
        session,
        image_tensor: np.ndarray,
        class_idx: int | None = None,
        input_name: str | None = None,
    ) -> str | None:
        if session is None:
            return None

        try:
            if input_name is None:
                input_name = session.get_inputs()[0].name

            outputs = session.run(None, {input_name: image_tensor})
            logits = outputs[0][0]

            if class_idx is None:
                class_idx = int(np.argmax(logits))

            gradient = self._compute_gradient(session, input_name, image_tensor, class_idx)
            if gradient is None:
                return None

            heatmap = self._compute_cam(gradient, image_tensor)
            heatmap_b64 = self._heatmap_to_base64(heatmap)
            return heatmap_b64
        except Exception:
            logger.warning("Grad-CAM generation failed", exc_info=True)
            return None

    def _compute_gradient(
        self,
        session,
        input_name: str,
        image_tensor: np.ndarray,
        class_idx: int,
    ) -> np.ndarray | None:
        try:
            import onnxruntime as ort

            input_meta = session.get_inputs()[0]
            output_meta = session.get_outputs()

            grad_output = np.zeros_like(output_meta[0].shape if output_meta else [1, 1000], dtype=np.float32)
            if grad_output.ndim >= 2:
                grad_output[0][class_idx] = 1.0

            return grad_output
        except Exception:
            return None

    def _compute_cam(self, gradient: np.ndarray, image_tensor: np.ndarray) -> np.ndarray:
        if gradient.ndim >= 2 and gradient.shape[-1] > 1:
            weights = np.mean(gradient[0] if gradient.ndim > 1 else gradient, axis=0)
        else:
            weights = gradient.flatten()

        spatial_size = image_tensor.shape[2] * image_tensor.shape[3] if image_tensor.ndim == 4 else 224 * 224
        min_len = min(len(weights), spatial_size)

        if min_len > 0:
            cam = np.zeros(spatial_size, dtype=np.float32)
            cam[:min_len] = weights[:min_len]
            cam = cam.reshape(image_tensor.shape[2], image_tensor.shape[3]) if image_tensor.ndim == 4 else cam.reshape(224, 224)
        else:
            cam = np.zeros((224, 224), dtype=np.float32)

        cam = np.maximum(cam, 0)
        cam_max = cam.max()
        if cam_max > 0:
            cam = cam / cam_max

        return cam

    def _heatmap_to_base64(self, heatmap: np.ndarray) -> str:
        try:
            from PIL import Image

            heatmap_resized = np.array(
                Image.fromarray((heatmap * 255).astype(np.uint8)).resize((224, 224), Image.BILINEAR)
            )
            colored = self._apply_colormap(heatmap_resized)
            img = Image.fromarray(colored)

            import io

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            logger.warning("Heatmap to base64 conversion failed", exc_info=True)
            return ""

    def _apply_colormap(self, heatmap: np.ndarray) -> np.ndarray:
        h, w = heatmap.shape
        colored = np.zeros((h, w, 3), dtype=np.uint8)

        for i in range(h):
            for j in range(w):
                val = heatmap[i, j] / 255.0
                if val < 0.25:
                    colored[i, j] = [0, 0, int(val * 4 * 255)]
                elif val < 0.5:
                    colored[i, j] = [0, int((val - 0.25) * 4 * 255), 255]
                elif val < 0.75:
                    colored[i, j] = [int((val - 0.5) * 4 * 255), 255, int((0.75 - val) * 4 * 255)]
                else:
                    colored[i, j] = [255, int((1.0 - val) * 4 * 255), 0]

        return colored

    def overlay_heatmap(
        self,
        image_pixels: np.ndarray,
        heatmap: np.ndarray,
        alpha: float = 0.4,
    ) -> np.ndarray:
        if image_pixels.ndim == 3 and image_pixels.shape[0] == 3:
            image_pixels = image_pixels.transpose(1, 2, 0)

        img_uint8 = (np.clip(image_pixels, 0, 1) * 255).astype(np.uint8)
        heatmap_resized = np.array(
            __import__("PIL").Image.fromarray((heatmap * 255).astype(np.uint8)).resize(
                (img_uint8.shape[1], img_uint8.shape[0])
            ),
            dtype=np.float32,
        ) / 255.0

        heatmap_colored = self._apply_colormap((heatmap_resized * 255).astype(np.uint8)).astype(np.float32) / 255.0

        overlay = (1 - alpha) * img_uint8.astype(np.float32) / 255.0 + alpha * heatmap_colored
        return (np.clip(overlay, 0, 1) * 255).astype(np.uint8)
