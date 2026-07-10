import logging

import numpy as np
import torch

from app.vision.xai.types import XAIReport, Detection, FeatureAttribution, ModelFeature
from app.vision.xai.gradcam import RealGradCAM, GradCAMFromAttention
from app.vision.xai.feature_attribution import FeatureAttributor
from app.vision.xai.uncertainty import UncertaintyEstimator
from app.vision.xai.concept_bridge import interpret_disease, map_features_to_agronomy
from app.vision.xai.lesion_analyzer import LesionAnalyzer
from app.vision.xai.heatmap_renderer import HeatmapRenderer

logger = logging.getLogger(__name__)


class XAIReportBuilder:
    def __init__(
        self,
        model: torch.nn.Module | None = None,
        target_layer: torch.nn.Module | None = None,
        mc_samples: int = 10,
    ):
        self.model = model
        self.target_layer = target_layer
        self.mc_samples = mc_samples
        self.lesion_analyzer = LesionAnalyzer()
        self.renderer = HeatmapRenderer()

    def build(
        self,
        image: np.ndarray,
        input_tensor: torch.Tensor,
        detections: list,
        disease_name: str,
        disease_probs: dict[str, float],
        severity_score: float,
        severity_label: str,
        weather: dict | None = None,
        model_versions: dict[str, str] | None = None,
    ) -> XAIReport:
        report = XAIReport()
        report.model_versions = model_versions or {}

        report.detections = [
            Detection(
                bbox=d.bbox if hasattr(d, "bbox") else (0, 0, 0, 0),
                class_label=d.class_label if hasattr(d, "class_label") else "unknown",
                confidence=d.confidence if hasattr(d, "confidence") else 0.0,
                area_pixels=d.area if hasattr(d, "area") else 0,
            )
            for d in detections
        ]

        report.predicted_class = disease_name
        report.confidence = max(disease_probs.values()) if disease_probs else 0.0
        report.class_probabilities = disease_probs

        report.gradcam_heatmap = self._generate_gradcam(input_tensor, disease_name)
        report.attention_map = self._generate_attention_map(input_tensor)
        report.feature_attribution = self._generate_feature_attribution(input_tensor)

        lesion_regions = []
        for det in detections:
            if hasattr(det, "class_label") and det.class_label != "healthy_leaf":
                bbox = det.bbox if hasattr(det, "bbox") else (0, 0, 0, 0)
                region = self.lesion_analyzer.analyze_region(image, bbox)
                lesion_regions.append(region)
        report.lesion_regions = lesion_regions

        h, w = image.shape[:2]
        image_area = h * w
        report.severity = self.lesion_analyzer.build_severity_explanation(
            detections, image_area, severity_score, severity_label
        )

        feature_names = [f.feature_name for f in report.feature_attribution.top_contributing_regions]
        feature_strengths = [f.contribution_score for f in report.feature_attribution.top_contributing_regions]
        report.model_features = map_features_to_agronomy(feature_names, feature_strengths)

        report.agronomic = interpret_disease(disease_name, severity_label, weather)

        if self.model is not None:
            try:
                from app.vision.xai.uncertainty import UncertaintyEstimator
                estimator = UncertaintyEstimator(self.model, self.mc_samples)
                report.uncertainty = estimator.estimate(input_tensor)
            except Exception:
                logger.debug("Uncertainty estimation skipped", exc_info=True)

        return report

    def _generate_gradcam(self, input_tensor: torch.Tensor, disease_name: str) -> str:
        if self.model is None or self.target_layer is None:
            return ""
        try:
            gradcam = RealGradCAM(self.model, self.target_layer)
            heatmap = gradcam.generate(input_tensor)
            gradcam.remove_hooks()
            if heatmap is not None and heatmap.any():
                from PIL import Image
                import io, base64
                heatmap_uint8 = (heatmap * 255).astype(np.uint8)
                heatmap_colored = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
                heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(heatmap_colored)
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            logger.debug("GradCAM generation failed", exc_info=True)
        return ""

    def _generate_attention_map(self, input_tensor: torch.Tensor) -> str:
        if self.model is None:
            return ""
        try:
            attn_gen = GradCAMFromAttention(self.model)
            attn = attn_gen.generate(input_tensor)
            if attn is not None:
                from PIL import Image
                import io, base64
                attn_uint8 = (np.clip(attn, 0, 1) * 255).astype(np.uint8)
                import cv2
                attn_colored = cv2.applyColorMap(attn_uint8, cv2.COLORMAP_VIRIDIS)
                attn_colored = cv2.cvtColor(attn_colored, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(attn_colored)
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            logger.debug("Attention map generation failed", exc_info=True)
        return ""

    def _generate_feature_attribution(self, input_tensor: torch.Tensor) -> FeatureAttribution:
        if self.model is None:
            return FeatureAttribution()
        try:
            attributor = FeatureAttributor(self.model)
            return attributor.compute_attribution(input_tensor)
        except Exception:
            logger.debug("Feature attribution failed", exc_info=True)
            return FeatureAttribution()
