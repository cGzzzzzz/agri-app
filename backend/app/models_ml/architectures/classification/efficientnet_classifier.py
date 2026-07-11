import torch
import torch.nn as nn
import torch.nn.functional as F


class ChannelAttention(nn.Module):
    def __init__(self, channels: int, reduction: int = 16):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(channels, channels // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(channels // reduction, channels, bias=False),
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, c, _, _ = x.size()
        avg_out = self.fc(self.avg_pool(x).view(b, c))
        max_out = self.fc(self.max_pool(x).view(b, c))
        out = avg_out + max_out
        return self.sigmoid(out).unsqueeze(-1).unsqueeze(-1) * x


class SpatialAttention(nn.Module):
    def __init__(self, kernel_size: int = 7):
        super().__init__()
        padding = kernel_size // 2
        self.conv = nn.Conv2d(2, 1, kernel_size, padding=padding, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out, _ = torch.max(x, dim=1, keepdim=True)
        combined = torch.cat([avg_out, max_out], dim=1)
        attention = self.sigmoid(self.conv(combined))
        return attention * x


class CBAM(nn.Module):
    def __init__(self, channels: int, reduction: int = 16, kernel_size: int = 7):
        super().__init__()
        self.channel_attention = ChannelAttention(channels, reduction)
        self.spatial_attention = SpatialAttention(kernel_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.channel_attention(x)
        x = self.spatial_attention(x)
        return x


class DiseaseClassifier(nn.Module):
    def __init__(
        self, num_classes: int, backbone: str = "efficientnet_b0", pretrained: bool = True
    ):
        super().__init__()
        self.num_classes = num_classes
        self.backbone_name = backbone

        try:
            import timm

            self.backbone = timm.create_model(backbone, pretrained=pretrained, num_classes=0)
            backbone_features = self.backbone.num_features
        except ImportError as err:
            raise ImportError("timm is required. Install with: pip install timm") from err

        self.attention = CBAM(backbone_features)
        self.classifier = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(backbone_features, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(256, num_classes),
        )

        self._grad_activations = None
        self._grad_gradients = None

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        features = self.backbone(x)
        if features.dim() == 2:
            features = features.unsqueeze(-1).unsqueeze(-1)
        attended = self.attention(features)
        pooled = F.adaptive_avg_pool2d(attended, 1).flatten(1)
        logits = self.classifier(pooled)
        return logits, pooled

    def predict_with_confidence(self, x: torch.Tensor) -> tuple[str, float, dict[str, float]]:
        self.eval()
        with torch.no_grad():
            logits, _ = self.forward(x)
            probs = F.softmax(logits, dim=1)
            confidence, predicted = torch.max(probs, dim=1)
            class_probs = (
                {name: float(probs[0, i]) for i, name in enumerate(self._class_names)}
                if hasattr(self, "_class_names")
                else {f"class_{i}": float(probs[0, i]) for i in range(self.num_classes)}
            )
        return (
            self._class_names[predicted.item()]
            if hasattr(self, "_class_names")
            else f"class_{predicted.item()}",
            confidence.item(),
            class_probs,
        )

    def get_attention_map(self, x: torch.Tensor) -> torch.Tensor:
        self.eval()
        with torch.no_grad():
            features = self.backbone(x)
            if features.dim() == 2:
                features = features.unsqueeze(-1).unsqueeze(-1)
            attended = self.attention(features)
        spatial_map = attended.mean(dim=1, keepdim=True)
        spatial_map = F.interpolate(
            spatial_map, size=(224, 224), mode="bilinear", align_corners=False
        )
        spatial_map = spatial_map - spatial_map.min()
        spatial_map = spatial_map / (spatial_map.max() + 1e-8)
        return spatial_map.squeeze()

    def set_class_names(self, names: list[str]):
        self._class_names = names

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
