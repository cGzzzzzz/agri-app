import base64
import io
import logging

import cv2
import numpy as np

from app.vision.xai.types import ColorProfile, LesionRegion, TextureFeatures

logger = logging.getLogger(__name__)


class LesionAnalyzer:
    def analyze_region(self, image: np.ndarray, bbox: tuple[int, int, int, int]) -> LesionRegion:
        x1, y1, x2, y2 = bbox
        h, w = image.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        patch = image[y1:y2, x1:x2]

        if patch.size == 0:
            return LesionRegion(bbox=bbox)

        color_profile = self._analyze_color(patch)
        texture = self._analyze_texture(patch)
        lesion_type = self._classify_lesion_type(color_profile, texture)
        crop_b64 = self._patch_to_base64(patch)

        return LesionRegion(
            crop_image_base64=crop_b64,
            bbox=bbox,
            lesion_type=lesion_type,
            area_ratio=0.0,
            color_profile=color_profile,
            texture_features=texture,
        )

    def _analyze_color(self, patch: np.ndarray) -> ColorProfile:
        hsv = cv2.cvtColor(patch, cv2.COLOR_RGB2HSV)
        h, s, v = cv2.split(hsv)

        hue_mean = float(np.mean(h))
        sat_mean = float(np.mean(s))
        bright_mean = float(np.mean(v))

        h_norm = h.astype(float) / 180.0
        green_mask = ((h_norm > 0.25) & (h_norm < 0.45) & (s > 50)).astype(float)
        brown_mask = ((h_norm > 0.05) & (h_norm < 0.15) & (s > 30) & (v < 200)).astype(float)
        gray_mask = ((s < 30) & (v > 50) & (v < 200)).astype(float)

        total = patch.shape[0] * patch.shape[1]
        green_ratio = float(np.sum(green_mask) / max(total, 1))
        brown_ratio = float(np.sum(brown_mask) / max(total, 1))
        gray_ratio = float(np.sum(gray_mask) / max(total, 1))

        return ColorProfile(
            dominant_hue=hue_mean,
            saturation_mean=sat_mean,
            brightness_mean=bright_mean,
            green_ratio=green_ratio,
            brown_ratio=brown_ratio,
            gray_ratio=gray_ratio,
        )

    def _analyze_texture(self, patch: np.ndarray) -> TextureFeatures:
        gray = cv2.cvtColor(patch, cv2.COLOR_RGB2GRAY)

        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.sum(edges > 0) / max(edges.size, 1))

        contrast = float(np.std(gray))

        kernel = np.ones((3, 3), np.float32) / 9
        smoothed = cv2.filter2D(gray.astype(float), -1, kernel)
        homogeneity = float(1.0 - np.std(gray.astype(float) - smoothed) / 128.0)

        is_necrotic = brown_ratio > 0.3 or gray_ratio > 0.2
        color_profile = self._analyze_color(patch)
        is_necrotic = color_profile.brown_ratio > 0.3 or color_profile.gray_ratio > 0.2

        return TextureFeatures(
            edge_density=edge_density,
            contrast=contrast,
            homogeneity=homogeneity,
            is_necrotic=is_necrotic,
        )

    def _classify_lesion_type(self, color: ColorProfile, texture: TextureFeatures) -> str:
        if color.brown_ratio > 0.4 and color.gray_ratio > 0.15:
            return "necrotic_lesion"
        if color.brown_ratio > 0.3:
            return "brown_spot"
        if color.green_ratio < 0.3 and color.saturation_mean < 100:
            return "chlorotic_spot"
        if texture.edge_density > 0.15:
            return "bacterial_lesion"
        return "early_lesion"

    def _patch_to_base64(self, patch: np.ndarray, max_size: int = 150) -> str:
        try:
            h, w = patch.shape[:2]
            scale = min(max_size / h, max_size / w, 1.0)
            if scale < 1.0:
                patch = cv2.resize(patch, (int(w * scale), int(h * scale)))
            img = __import__("PIL").Image.fromarray(patch)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            return ""

    def compute_lesion_area_ratio(self, detections: list, image_area: int) -> float:
        lesion_area = sum(
            max(0, d[1][2] - d[1][0]) * max(0, d[1][3] - d[1][1])
            for d in detections
            if len(d) >= 2
            and not (hasattr(d[0], "class_label") and d[0].class_label == "healthy_leaf")
        )
        return min(1.0, lesion_area / max(image_area, 1))

    def build_severity_explanation(
        self,
        detections: list,
        image_area: int,
        severity_score: float,
        severity_label: str,
        color_degradation: float = 0.0,
    ) -> "SeverityExplanation":
        from app.vision.xai.types import SeverityExplanation

        lesion_dets = [
            d
            for d in detections
            if not (hasattr(d, "class_label") and d.class_label == "healthy_leaf")
        ]
        areas = []
        for det in lesion_dets:
            if hasattr(det, "area"):
                areas.append(det.area)
            elif isinstance(det, tuple) and len(det) >= 2:
                bbox = det[1] if isinstance(det[1], (list, tuple)) else det
                areas.append(max(0, bbox[2] - bbox[0]) * max(0, bbox[3] - bbox[1]))

        total_lesion = sum(areas)
        largest = max(areas) if areas else 0
        ratio = min(1.0, total_lesion / max(image_area, 1))

        reasoning = []
        reasoning.append(f"Total lesion area: {ratio * 100:.1f}% of visible leaf surface")
        reasoning.append(f"{len(lesion_dets)} distinct lesions detected")
        if largest > 0:
            reasoning.append(
                f"Largest lesion covers {largest / max(image_area, 1) * 100:.1f}% of leaf"
            )
        if color_degradation > 0.3:
            reasoning.append(
                f"Color analysis shows significant tissue degradation ({color_degradation:.0%})"
            )

        return SeverityExplanation(
            lesion_area_ratio=ratio,
            lesion_count=len(lesion_dets),
            largest_lesion_area=largest / max(image_area, 1),
            affected_leaf_percentage=ratio,
            color_degradation=color_degradation,
            severity_score=severity_score,
            severity_label=severity_label,
            reasoning=reasoning,
        )
