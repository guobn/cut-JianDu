"""Tests for ModelFactory class"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.model_factory import ModelFactory, get_model_factory
from app.models.detection import ModelType


@pytest.fixture
def model_factory():
    """Create fresh ModelFactory instance for each test"""
    return ModelFactory()


class TestModelType:
    """Test ModelType enum integration"""

    def test_model_type_enum_values(self):
        """Test all model type values"""
        assert ModelType.YOLOV8.value == "yolov8"
        assert ModelType.APS_YOLO.value == "aps-yolo"
        assert ModelType.DECONV_YOLO.value == "deconv-yolo"
        assert ModelType.RGA_CRNN.value == "rga-crnn"


class TestModelFactoryGetModel:
    """Test ModelFactory.get_model() method"""

    def test_get_model_invalid_type(self, model_factory):
        """Test invalid model type raises exception"""
        with pytest.raises(ValueError, match="Unsupported model type"):
            model_factory.get_model("invalid-model")

    def test_get_model_yolov8_not_configured(self, model_factory):
        """Test YOLOv8 returns None when not configured"""
        with patch('app.services.model_factory.settings') as mock_settings:
            mock_settings.yolov8_slip_model_path = None
            model = model_factory.get_model(ModelType.YOLOV8, use_fallback=False)
            assert model is None

    def test_get_model_caches_result(self, model_factory):
        """Test that loaded models are cached"""
        with patch('app.services.model_factory.settings') as mock_settings:
            mock_settings.yolov8_slip_model_path = "/fake/path.pt"

            with patch.object(model_factory, '_load_yolov8') as mock_load:
                mock_model = Mock()
                mock_load.return_value = mock_model

                # First call
                result1 = model_factory.get_model(ModelType.YOLOV8, use_fallback=False)
                # Second call
                result2 = model_factory.get_model(ModelType.YOLOV8, use_fallback=False)

                # Should only load once
                assert mock_load.call_count == 1
                assert result1 is result2

    def test_clear_cache(self, model_factory):
        """Test clear_cache removes loaded models"""
        with patch('app.services.model_factory.settings') as mock_settings:
            mock_settings.yolov8_slip_model_path = "/fake/path.pt"

            with patch.object(model_factory, '_load_yolov8') as mock_load:
                mock_model = Mock()
                mock_load.return_value = mock_model

                model_factory.get_model(ModelType.YOLOV8, use_fallback=False)
                model_factory.clear_cache()

                # Cache cleared, should load again
                model_factory.get_model(ModelType.YOLOV8, use_fallback=False)
                assert mock_load.call_count == 2


class TestModelFactoryFallback:
    """Test ModelFactory fallback mechanism"""

    def test_get_model_with_fallback_chain(self, model_factory):
        """Test fallback to YOLOv8 when primary model fails"""
        with patch('app.services.model_factory.settings') as mock_settings:
            # All primary models not configured
            mock_settings.aps_yolo_model_path = None
            mock_settings.deconv_yolo_model_path = None
            mock_settings.yolov8_slip_model_path = None

            # Request APS-YOLO, should fallback through chain
            model = model_factory.get_model(ModelType.APS_YOLO, use_fallback=True)
            # All failed, returns None
            assert model is None

    def test_get_model_fallback_success(self, model_factory):
        """Test fallback to available model"""
        with patch('app.services.model_factory.settings') as mock_settings:
            # APS-YOLO not configured
            mock_settings.aps_yolo_model_path = None
            # YOLOv8 configured
            mock_settings.yolov8_slip_model_path = "/fake/yolov8.pt"

            with patch.object(model_factory, '_load_yolov8') as mock_load_yolo:
                mock_model = Mock()
                mock_load_yolo.return_value = mock_model

                # Request APS-YOLO, should fallback to YOLOv8
                model = model_factory.get_model(ModelType.APS_YOLO, use_fallback=True)
                assert model is mock_model


class TestGetModelFactorySingleton:
    """Test get_model_factory() singleton function"""

    def test_get_model_factory_returns_singleton(self):
        """Test get_model_factory returns same instance"""
        factory1 = get_model_factory()
        factory2 = get_model_factory()
        assert factory1 is factory2


class TestModelFactoryModelSpecific:
    """Test model-specific loading methods"""

    def test_load_yolov8_ultralytics_not_available(self, model_factory):
        """Test YOLOv8 loading when ultralytics not installed"""
        with patch('app.services.model_factory._YOLO_AVAILABLE', False):
            result = model_factory._load_yolov8()
            assert result is None

    def test_load_rga_crnn_torch_not_available(self, model_factory):
        """Test RGA-CRNN loading when torch not installed"""
        with patch('app.services.model_factory._TORCH_AVAILABLE', False):
            result = model_factory._load_rga_crnn()
            assert result is None

    def test_load_yolov8_file_not_exists(self, model_factory):
        """Test YOLOv8 loading when file doesn't exist"""
        with patch('app.services.model_factory.settings') as mock_settings:
            mock_settings.yolov8_slip_model_path = "/nonexistent/path.pt"
            result = model_factory._load_yolov8()
            assert result is None

    def test_load_yolov12_not_configured(self, model_factory):
        """Test YOLOv12 returns None when not configured"""
        with patch('app.services.model_factory.settings') as mock_settings:
            mock_settings.yolov12_slip_model_path = None
            result = model_factory._load_yolov12()
            assert result is None

    def test_load_yolov12_ultralytics_not_available(self, model_factory):
        """Test YOLOv12 loading when ultralytics not installed"""
        with patch('app.services.model_factory._YOLO_AVAILABLE', False):
            with patch('app.services.model_factory.settings') as mock_settings:
                mock_settings.yolov12_slip_model_path = "/fake/path.pt"
                result = model_factory._load_yolov12()
                assert result is None
