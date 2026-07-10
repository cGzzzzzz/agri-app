import numpy as np
from pathlib import Path

from app.orchestrator.input_types import ProcessedImage
from app.vision.image_processor import RealImagePreprocessor


class ImagePreprocessorStage:
    def __init__(self, preprocessor: RealImagePreprocessor | None = None):
        self.preprocessor = preprocessor or RealImagePreprocessor()

    def process(self, state: dict) -> ProcessedImage:
        input_data = state.get("input")
        if input_data is None:
            raise ValueError("No input data in pipeline state")

        image_path = Path(input_data.image_path)
        processed = self.preprocessor.process(image_path, input_data.crop_override)

        return ProcessedImage(
            image_path=processed.image_path,
            pixels=processed.pixels,
            tensor=processed.tensor,
            original_size=processed.original_size,
            image_format=processed.image_format,
            quality_warnings=processed.quality_warnings,
        )
