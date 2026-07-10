import torch
import torch.nn as nn

from app.models_ml.architectures.classification.efficientnet_classifier import DiseaseClassifier


class CropClassifier(nn.Module):
    CROP_CLASSES = ["Rice", "Tomato", "Wheat", "Maize", "Cotton", "Sugarcane", "Banana"]

    def __init__(self, num_classes: int = 7, backbone: str = "efficientnet_b0", pretrained: bool = True):
        super().__init__()
        self.classifier = DiseaseClassifier(num_classes, backbone, pretrained)
        self.classifier.set_class_names(self.CROP_CLASSES[:num_classes])

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        return self.classifier(x)

    def predict(self, x: torch.Tensor) -> tuple[str, float, dict[str, float]]:
        return self.classifier.predict_with_confidence(x)

    def get_attention_map(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier.get_attention_map(x)
