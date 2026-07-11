class ModelLifecycleError(Exception):
    """Base error for model lifecycle and inference failures."""


class ModelUnavailableError(ModelLifecycleError):
    def __init__(self, task: str, crop: str | None = None, reason: str | None = None):
        self.task = task
        self.crop = crop
        self.reason = reason or "No registered model artifact is available."
        target = f" for crop '{crop}'" if crop else ""
        super().__init__(f"{task} model unavailable{target}: {self.reason}")


class ModelInferenceError(ModelLifecycleError):
    def __init__(self, model_name: str, reason: str):
        self.model_name = model_name
        self.reason = reason
        super().__init__(f"Inference failed for model '{model_name}': {reason}")
