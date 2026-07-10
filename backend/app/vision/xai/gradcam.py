import base64
import io
import logging
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class RealGradCAM:
    def __init__(self, model: torch.nn.Module, target_layer: torch.nn.Module):
        self.model = model
        self.target_layer = target_layer
        self.activations = None
        self.gradients = None
        self._hooks = []
        self._register_hooks()

    def _register_hooks(self):
        h1 = self.target_layer.register_forward_hook(self._forward_hook)
        h2 = self.target_layer.register_full_backward_hook(self._backward_hook)
        self._hooks.extend([h1, h2])

    def _forward_hook(self, module, input, output):
        self.activations = output.detach()

    def _backward_hook(self, module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def remove_hooks(self):
        for h in self._hooks:
            h.remove()
        self._hooks.clear()

    def generate(self, input_tensor: torch.Tensor, class_idx: int | None = None) -> np.ndarray:
        self.model.eval()
        output = self.model(input_tensor)
        if isinstance(output, tuple):
            output = output[0]

        if class_idx is None:
            class_idx = output.argmax(dim=1).item()

        self.model.zero_grad()
        output[0, class_idx].backward()

        if self.gradients is None or self.activations is None:
            return np.zeros((224, 224))

        weights = self.gradients.mean(dim=(2, 3), keepdim=True)
        cam = (weights * self.activations).sum(dim=1, keepdim=True)
        cam = F.relu(cam)
        cam = F.interpolate(cam, size=(224, 224), mode="bilinear", align_corners=False)
        cam = cam - cam.min()
        cam = cam / (cam.max() + 1e-8)
        return cam.squeeze().cpu().numpy()

    def generate_multiple(self, input_tensor: torch.Tensor, class_indices: list[int]) -> dict[int, np.ndarray]:
        results = {}
        for idx in class_indices:
            results[idx] = self.generate(input_tensor, idx)
        return results


class GradCAMFromAttention:
    def __init__(self, model: torch.nn.Module):
        self.model = model

    def generate(self, input_tensor: torch.Tensor) -> np.ndarray | None:
        try:
            if hasattr(self.model, "get_attention_map"):
                attn = self.model.get_attention_map(input_tensor)
                if isinstance(attn, torch.Tensor):
                    return attn.cpu().numpy()
        except Exception:
            logger.warning("Attention-based GradCAM failed", exc_info=True)
        return None
