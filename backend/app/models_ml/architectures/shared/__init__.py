import numpy as np
import torch
import torch.nn as nn  # noqa: F401


class ImageNetNormalize:
    MEAN = [0.485, 0.456, 0.406]
    STD = [0.229, 0.224, 0.225]

    def __call__(self, tensor: torch.Tensor) -> torch.Tensor:
        mean = torch.tensor(self.MEAN, dtype=tensor.dtype, device=tensor.device).view(1, 3, 1, 1)
        std = torch.tensor(self.STD, dtype=tensor.dtype, device=tensor.device).view(1, 3, 1, 1)
        return (tensor - mean) / std


def get_train_transforms(img_size: int = 224):
    try:
        import albumentations as A
        from albumentations.pytorch import ToTensorV2

        return A.Compose(
            [
                A.RandomResizedCrop(img_size, img_size, scale=(0.8, 1.0), p=0.5),
                A.HorizontalFlip(p=0.5),
                A.VerticalFlip(p=0.3),
                A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.3),
                A.HueSaturationValue(
                    hue_shift_limit=10, sat_shift_limit=20, val_shift_limit=10, p=0.2
                ),
                A.GaussNoise(var_limit=(10.0, 50.0), p=0.1),
                A.Normalize(mean=ImageNetNormalize.MEAN, std=ImageNetNormalize.STD),
                ToTensorV2(),
            ]
        )
    except ImportError:
        return None


def get_val_transforms(img_size: int = 224):
    try:
        import albumentations as A
        from albumentations.pytorch import ToTensorV2

        return A.Compose(
            [
                A.Resize(img_size, img_size),
                A.Normalize(mean=ImageNetNormalize.MEAN, std=ImageNetNormalize.STD),
                ToTensorV2(),
            ]
        )
    except ImportError:
        return None


def numpy_to_tensor(image: np.ndarray, img_size: int = 224) -> torch.Tensor:
    from PIL import Image

    if image.ndim == 2:
        image = np.stack([image] * 3, axis=-1)
    if image.shape[-1] == 4:
        image = image[:, :, :3]

    img = Image.fromarray(image).convert("RGB").resize((img_size, img_size))
    arr = np.array(img, dtype=np.float32) / 255.0
    arr = (arr - np.array(ImageNetNormalize.MEAN)) / np.array(ImageNetNormalize.STD)
    tensor = torch.from_numpy(arr.transpose(2, 0, 1))
    return tensor.unsqueeze(0)


def compute_lesion_area_ratio(detections: list, image_area: int) -> float:
    lesion_area = sum(d.area for d in detections if d.class_label != "healthy_leaf")
    return min(1.0, lesion_area / max(image_area, 1))


def crop_region(image: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
    x1, y1, x2, y2 = bbox
    h, w = image.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    return image[y1:y2, x1:x2]
