"""
Model Factory - Dynamic model loading with fallback mechanism

Supports:
- YOLOv8 (baseline)
- YOLOv11_FINETUNED (微调模型，用于单支简牍检测)
"""
import logging
from pathlib import Path
from typing import Optional, Any, Dict
from app.config import settings
from app.models.detection import ModelType

# Optional imports
try:
    from ultralytics import YOLO
    _YOLO_AVAILABLE = True
except ImportError:
    _YOLO_AVAILABLE = False
    YOLO = None

try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
    torch = None


class ModelFactory:
    """Factory for loading detection models with fallback mechanism"""

    def __init__(self):
        self._model_cache: Dict[ModelType, Any] = {}
        self._logger = logging.getLogger(__name__)

    def get_model(self, model_type: ModelType, use_fallback: bool = True):
        """
        Get detection model instance

        Args:
            model_type: Requested model type
            use_fallback: If True, fallback to YOLOv8 when primary fails

        Returns:
            Loaded model instance or None if unavailable
        """
        # Check cache first
        if model_type in self._model_cache:
            return self._model_cache[model_type]

        # Try to load requested model
        model = self._load_model(model_type)

        if model is not None:
            self._model_cache[model_type] = model
            return model

        # Fallback chain if enabled (only YOLOv8 and YOLOv11_FINETUNED)
        if use_fallback:
            self._logger.info("Model %s unavailable, attempting fallback", model_type)
            fallback_order = [
                ModelType.YOLOV8,
                ModelType.YOLOV11_FINETUNED,
            ]

            for fallback_type in fallback_order:
                if fallback_type == model_type:
                    continue
                fallback_model = self._load_model(fallback_type)
                if fallback_model is not None:
                    self._logger.info("Fallback to %s successful", fallback_type)
                    return fallback_model

        self._logger.warning("No model available for %s and all fallbacks failed", model_type)
        return None

    def _load_model(self, model_type: ModelType) -> Optional[Any]:
        """Load specific model type"""
        loaders = {
            ModelType.YOLOV8: self._load_yolov8,
            ModelType.YOLOV11_FINETUNED: self._load_yolov11_finetuned,
        }

        loader = loaders.get(model_type)
        if not loader:
            raise ValueError(f"Unsupported model type: {model_type}")

        return loader()

    def _load_yolov8(self) -> Optional[Any]:
        """Load YOLOv8 slip detection model"""
        if not _YOLO_AVAILABLE:
            self._logger.debug("YOLOv8: ultralytics not available")
            return None

        model_path = getattr(settings, "yolov8_slip_model_path", None)
        if not model_path:
            return None

        path = self._resolve_model_path(model_path)
        if not path.exists():
            self._logger.warning("YOLOv8 model file not found: %s", path)
            return None

        try:
            model = YOLO(str(path))
            self._logger.info("YOLOv8 model loaded: %s", path)
            return model
        except Exception as e:
            self._logger.warning("YOLOv8 load failed: %s", e)
            return None

    def _load_yolov11_finetuned(self) -> Optional[Any]:
        """
        Load YOLOv11 微调模型 (bestSingle.pt)

        用于单支简牍检测
        Config: yolov11_finetuned_model_path in settings
        """
        if not _YOLO_AVAILABLE:
            self._logger.debug("YOLOv11_FINETUNED: ultralytics not available")
            return None

        model_path = getattr(settings, "yolov11_finetuned_model_path", None)
        if not model_path:
            self._logger.debug("YOLOv11_FINETUNED: model path not configured")
            return None

        path = self._resolve_model_path(model_path)
        if not path.exists():
            self._logger.warning("YOLOv11_FINETUNED model file not found: %s", path)
            return None

        try:
            model = YOLO(str(path))
            self._logger.info("YOLOv11_FINETUNED model loaded: %s", path)
            return model
        except Exception as e:
            self._logger.warning("YOLOv11_FINETUNED load failed: %s", e)
            return None

    def _resolve_model_path(self, model_path: str) -> Path:
        """Resolve model path relative to project root if not absolute"""
        path = Path(model_path)
        if not path.is_absolute():
            base = Path(__file__).resolve().parent.parent.parent
            path = base / model_path
        return path

    def get_model_info(self, model_type: ModelType) -> Dict[str, Any]:
        """
        Get model information

        Returns:
            Dict with 'available', 'path', 'loaded' keys
        """
        path_attr_map = {
            ModelType.YOLOV8: "yolov8_slip_model_path",
            ModelType.YOLOV11_FINETUNED: "yolov11_finetuned_model_path",
        }

        path_attr = path_attr_map.get(model_type)
        model_path = getattr(settings, path_attr, None) if path_attr else None

        return {
            "model_type": model_type.value,
            "available": model_path is not None,
            "path": model_path,
            "loaded": model_type in self._model_cache,
        }

    def clear_cache(self):
        """Clear loaded model cache"""
        self._model_cache.clear()
        self._logger.info("Model cache cleared")


# Singleton instance
_model_factory: Optional[ModelFactory] = None


def get_model_factory() -> ModelFactory:
    """Get singleton ModelFactory instance"""
    global _model_factory
    if _model_factory is None:
        _model_factory = ModelFactory()
    return _model_factory
