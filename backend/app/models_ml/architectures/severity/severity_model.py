import torch
import torch.nn as nn
import torch.nn.functional as F


class SeverityModel(nn.Module):
    SEVERITY_CLASSES = ["none", "low", "moderate", "high"]

    def __init__(self, backbone: str = "efficientnet_b0", pretrained: bool = True):
        super().__init__()
        try:
            import timm

            self.backbone = timm.create_model(backbone, pretrained=pretrained, num_classes=0)
            features = self.backbone.num_features
        except ImportError as err:
            raise ImportError("timm is required. Install with: pip install timm") from err

        self.regressor = nn.Sequential(
            nn.Linear(features, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(128, 1),
            nn.Sigmoid(),
        )
        self.classifier = nn.Sequential(
            nn.Linear(features, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.1),
            nn.Linear(64, len(self.SEVERITY_CLASSES)),
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        features = self.backbone(x)
        if features.dim() == 2:
            features = features.unsqueeze(-1).unsqueeze(-1)
        pooled = F.adaptive_avg_pool2d(features, 1).flatten(1)
        severity_score = self.regressor(pooled)
        severity_logits = self.classifier(pooled)
        return severity_score, severity_logits

    def predict(self, x: torch.Tensor) -> tuple[float, str, dict[str, float]]:
        self.eval()
        with torch.no_grad():
            score, logits = self.forward(x)
            probs = F.softmax(logits, dim=1)
            confidence, predicted = torch.max(probs, dim=1)
            score_val = score.item()
            label = self.SEVERITY_CLASSES[predicted.item()]
            class_probs = {name: float(probs[0, i]) for i, name in enumerate(self.SEVERITY_CLASSES)}
        return score_val, label, class_probs

    def get_attention_map(self, x: torch.Tensor) -> torch.Tensor:
        self.eval()
        with torch.no_grad():
            features = self.backbone(x)
            if features.dim() == 2:
                features = features.unsqueeze(-1).unsqueeze(-1)
        spatial_map = features.mean(dim=1, keepdim=True)
        spatial_map = F.interpolate(
            spatial_map, size=(224, 224), mode="bilinear", align_corners=False
        )
        spatial_map = spatial_map - spatial_map.min()
        spatial_map = spatial_map / (spatial_map.max() + 1e-8)
        return spatial_map.squeeze()

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
