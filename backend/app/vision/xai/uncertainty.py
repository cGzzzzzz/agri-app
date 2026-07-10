import logging
import math

import numpy as np
import torch
import torch.nn.functional as F

from app.vision.xai.types import UncertaintyEstimate

logger = logging.getLogger(__name__)


class UncertaintyEstimator:
    def __init__(self, model: torch.nn.Module, mc_samples: int = 10):
        self.model = model
        self.mc_samples = mc_samples

    def estimate(self, input_tensor: torch.Tensor) -> UncertaintyEstimate:
        self.model.train()
        mc_predictions = []

        try:
            for _ in range(self.mc_samples):
                with torch.no_grad():
                    output = self.model(input_tensor)
                    if isinstance(output, tuple):
                        output = output[0]
                    probs = F.softmax(output, dim=1)
                    mc_predictions.append(probs.cpu().numpy())
        except Exception:
            logger.warning("MC Dropout estimation failed", exc_info=True)
            return self._fallback(input_tensor)

        if not mc_predictions:
            return self._fallback(input_tensor)

        mc_array = np.stack(mc_predictions, axis=0)
        mean_probs = mc_array.mean(axis=0)[0]

        epistemic = float(np.mean([np.var(mc_array[:, 0, c]) for c in range(mean_probs.shape[0])]))
        entropy = -float(np.sum(mean_probs * np.log(mean_probs + 1e-10)))
        max_entropy = math.log(len(mean_probs))
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

        aleatoric = float(normalized_entropy * 0.5)
        total = aleatoric + epistemic

        confidence = float(np.max(mean_probs))
        calibration = min(1.0, confidence + (1 - total) * 0.3)

        warning = None
        if total > 0.5:
            warning = "High uncertainty — prediction may be unreliable. Consider re-scanning."
        elif total > 0.3:
            warning = "Moderate uncertainty — verify with a second image if possible."
        elif confidence < 0.5:
            warning = "Low confidence — the model is uncertain about this classification."

        self.model.eval()
        return UncertaintyEstimate(
            aleatoric=aleatoric,
            epistemic=epistemic,
            total=total,
            calibration_score=calibration,
            prediction_entropy=normalized_entropy,
            warning=warning,
        )

    def _fallback(self, input_tensor: torch.Tensor) -> UncertaintyEstimate:
        self.model.eval()
        with torch.no_grad():
            output = self.model(input_tensor)
            if isinstance(output, tuple):
                output = output[0]
            probs = F.softmax(output, dim=1)
            confidence = float(probs.max())
            entropy = -float((probs * torch.log(probs + 1e-10)).sum())
            max_entropy = math.log(probs.shape[1])
            normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

        warning = None
        if confidence < 0.5:
            warning = "Low confidence — the model is uncertain about this classification."
        elif confidence < 0.7:
            warning = "Moderate confidence — consider verifying with another image."

        return UncertaintyEstimate(
            aleatoric=float(normalized_entropy * 0.5),
            epistemic=0.0,
            total=float(normalized_entropy * 0.5),
            calibration_score=confidence,
            prediction_entropy=float(normalized_entropy),
            warning=warning,
        )
