import logging

import numpy as np
import torch
import torch.nn.functional as F

from app.vision.xai.types import FeatureAttribution, RegionContribution

logger = logging.getLogger(__name__)


class FeatureAttributor:
    def __init__(self, model: torch.nn.Module, steps: int = 50):
        self.model = model
        self.steps = steps

    def integrated_gradients(
        self,
        input_tensor: torch.Tensor,
        class_idx: int | None = None,
    ) -> np.ndarray:
        self.model.eval()
        baseline = torch.zeros_like(input_tensor)

        output = self.model(input_tensor)
        if isinstance(output, tuple):
            output = output[0]
        if class_idx is None:
            class_idx = output.argmax(dim=1).item()

        scaled_inputs = [
            baseline + (float(i) / self.steps) * (input_tensor - baseline)
            for i in range(self.steps + 1)
        ]
        scaled_inputs = torch.cat(scaled_inputs, dim=0)
        scaled_inputs.requires_grad_(True)

        output = self.model(scaled_inputs)
        if isinstance(output, tuple):
            output = output[0]
        scores = output[:, class_idx]
        scores.sum().backward()

        gradients = scaled_inputs.grad.detach()
        avg_gradients = gradients[1:].mean(dim=0, keepdim=True)
        attributed = (input_tensor - baseline) * avg_gradients
        attr_map = attributed.sum(dim=1, keepdim=True)
        attr_map = F.interpolate(attr_map, size=(224, 224), mode="bilinear", align_corners=False)
        attr_map = attr_map.squeeze().abs()
        attr_map = attr_map - attr_map.min()
        attr_map = attr_map / (attr_map.max() + 1e-8)
        return attr_map.cpu().numpy()

    def smooth_grad(
        self,
        input_tensor: torch.Tensor,
        class_idx: int | None = None,
        n_samples: int = 20,
        sigma: float = 0.1,
    ) -> np.ndarray:
        self.model.eval()
        output = self.model(input_tensor)
        if isinstance(output, tuple):
            output = output[0]
        if class_idx is None:
            class_idx = output.argmax(dim=1).item()

        total_attr = torch.zeros_like(input_tensor)
        for _ in range(n_samples):
            noise = torch.randn_like(input_tensor) * sigma
            noisy_input = (input_tensor + noise).detach().requires_grad_(True)
            out = self.model(noisy_input)
            if isinstance(out, tuple):
                out = out[0]
            out[0, class_idx].backward()
            total_attr += noisy_input.grad.detach()

        avg_attr = total_attr / n_samples
        attr_map = avg_attr.sum(dim=1, keepdim=True)
        attr_map = F.interpolate(attr_map, size=(224, 224), mode="bilinear", align_corners=False)
        attr_map = attr_map.squeeze().abs()
        attr_map = attr_map - attr_map.min()
        attr_map = attr_map / (attr_map.max() + 1e-8)
        return attr_map.cpu().numpy()

    def compute_attribution(
        self,
        input_tensor: torch.Tensor,
        class_idx: int | None = None,
    ) -> FeatureAttribution:
        try:
            ig_map = self.integrated_gradients(input_tensor, class_idx)
        except Exception:
            logger.warning("Integrated Gradients failed, falling back to SmoothGrad", exc_info=True)
            try:
                ig_map = self.smooth_grad(input_tensor, class_idx)
            except Exception:
                ig_map = np.zeros((224, 224))

        regions = self._extract_top_regions(ig_map)

        gradient_norm = float(np.linalg.norm(ig_map))

        return FeatureAttribution(
            pixel_importance_map="",
            top_contributing_regions=regions,
            gradient_norm=gradient_norm,
        )

    def _extract_top_regions(self, attr_map: np.ndarray, top_k: int = 5) -> list[RegionContribution]:
        h, w = attr_map.shape
        regions = []
        region_size = h // 3
        for i in range(3):
            for j in range(3):
                y1, y2 = i * region_size, min((i + 1) * region_size, h)
                x1, x2 = j * region_size, min((j + 1) * region_size, w)
                score = float(attr_map[y1:y2, x1:x2].mean())
                location = self._region_name(i, j)
                regions.append(RegionContribution(
                    region_description=location,
                    contribution_score=score,
                    feature_type="color" if score > 0.3 else "texture",
                ))
        regions.sort(key=lambda r: r.contribution_score, reverse=True)
        return regions[:top_k]

    def _region_name(self, row: int, col: int) -> str:
        vertical = ["top", "middle", "bottom"]
        horizontal = ["left", "center", "right"]
        return f"{vertical[row]}_{horizontal[col]}_region"
