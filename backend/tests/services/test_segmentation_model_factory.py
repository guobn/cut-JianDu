"""Tests for ModelFactory integration in SegmentationService"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from app.services.segmentation_service import SegmentationService
from app.models.detection import DetectionParameters, ModelType


@pytest.fixture
def segmentation_service():
    """Create SegmentationService instance"""
    return SegmentationService()


@pytest.fixture
def sample_image():
    """Create a sample test image"""
    return np.zeros((500, 500, 3), dtype=np.uint8)


class TestSegmentationServiceModelFactory:
    """Test SegmentationService ModelFactory integration"""

    def test_init_uses_model_factory(self, segmentation_service):
        """Test SegmentationService initializes with ModelFactory"""
        assert hasattr(segmentation_service, '_model_factory')
        assert segmentation_service._model_factory is not None

    def test_detect_single_slips_uses_model_factory(self, segmentation_service, sample_image):
        """Test slip detection uses ModelFactory.get_model()"""
        with patch.object(segmentation_service._model_factory, 'get_model') as mock_get:
            mock_model = Mock()
            mock_get.return_value = mock_model

            # Mock _detect_single_slips_yolo to avoid actual YOLO inference
            with patch.object(segmentation_service, '_detect_single_slips_yolo') as mock_yolo:
                mock_yolo.return_value = []

                segmentation_service.detect_single_slips(sample_image)

                # Should call get_model with default YOLOV8
                mock_get.assert_called_once_with(ModelType.YOLOV8, use_fallback=True)

    def test_detect_single_slips_with_custom_model_type(self, segmentation_service, sample_image):
        """Test slip detection respects custom model_type"""
        with patch.object(segmentation_service._model_factory, 'get_model') as mock_get:
            mock_model = Mock()
            mock_get.return_value = mock_model

            with patch.object(segmentation_service, '_detect_single_slips_yolo') as mock_yolo:
                mock_yolo.return_value = []

                params = DetectionParameters(model_type=ModelType.APS_YOLO)
                segmentation_service.detect_single_slips(sample_image, params)

                # Should call get_model with APS_YOLO
                mock_get.assert_called_once_with(ModelType.APS_YOLO, use_fallback=True)

    def test_detect_single_slips_fallback_to_opencv(self, segmentation_service, sample_image):
        """Test slip detection falls back to OpenCV when no model available"""
        with patch.object(segmentation_service._model_factory, 'get_model') as mock_get:
            mock_get.return_value = None

            with patch.object(segmentation_service, '_detect_single_slips_opencv') as mock_opencv:
                mock_opencv.return_value = []

                segmentation_service.detect_single_slips(sample_image)

                # Should call OpenCV fallback
                mock_opencv.assert_called_once()

    def test_detect_single_slips_logs_model_usage(self, segmentation_service, sample_image, caplog):
        """Test slip detection logs which model is being used"""
        import logging
        with patch.object(segmentation_service._model_factory, 'get_model') as mock_get:
            mock_model = Mock()
            mock_get.return_value = mock_model

            with patch.object(segmentation_service, '_detect_single_slips_yolo') as mock_yolo:
                mock_yolo.return_value = []

                with caplog.at_level(logging.INFO):
                    params = DetectionParameters(model_type=ModelType.APS_YOLO)
                    segmentation_service.detect_single_slips(sample_image, params)

                    assert "使用 aps-yolo 模型进行单支检测" in caplog.text


class TestDetectSingleCharactersModelFactory:
    """Test character detection ModelFactory integration"""

    def test_detect_characters_with_rga_crnn(self, segmentation_service, sample_image):
        """Test character detection uses RGA-CRNN when specified"""
        with patch.object(segmentation_service._model_factory, 'get_model') as mock_get:
            mock_model = Mock()
            mock_get.return_value = mock_model

            # Mock the RGA-CRNN detection method
            with patch.object(segmentation_service, '_detect_single_characters_rga_crnn') as mock_rga:
                mock_rga.return_value = []

                params = DetectionParameters(model_type=ModelType.RGA_CRNN)
                segmentation_service.detect_single_characters(sample_image, params)

                # Should call get_model for RGA-CRNN
                mock_get.assert_called_once_with(ModelType.RGA_CRNN, use_fallback=False)
                mock_rga.assert_called_once()

    def test_detect_characters_fallback_to_torchscript(self, segmentation_service, sample_image):
        """Test character detection falls back to TorchScript when RGA-CRNN unavailable"""
        with patch.object(segmentation_service._model_factory, 'get_model') as mock_get:
            mock_get.return_value = None

            # Mock TorchScript model loading
            with patch.object(segmentation_service, '_get_char_torchscript_model') as mock_torch:
                mock_torch.return_value = None  # No TorchScript either

                with patch.object(segmentation_service, '_detect_characters_opencv') as mock_opencv:
                    mock_opencv.return_value = []

                    params = DetectionParameters(model_type=ModelType.RGA_CRNN)
                    segmentation_service.detect_single_characters(sample_image, params)

                    # Should fall back to OpenCV
                    mock_opencv.assert_called_once()

    def test_detect_characters_default_uses_torchscript(self, segmentation_service, sample_image):
        """Test character detection uses TorchScript by default"""
        with patch.object(segmentation_service, '_get_char_torchscript_model') as mock_torch:
            mock_torch.return_value = None

            with patch.object(segmentation_service, '_detect_characters_opencv') as mock_opencv:
                mock_opencv.return_value = []

                segmentation_service.detect_single_characters(sample_image)

                # Should try to load TorchScript
                mock_torch.assert_called_once()


class TestRgaCrnnDetection:
    """Test RGA-CRNN detection method"""

    def test_rga_crnn_calls_torchscript_implementation(self, segmentation_service, sample_image):
        """Test RGA-CRNN detection delegates to TorchScript implementation"""
        mock_model = Mock()
        params = DetectionParameters()

        with patch.object(segmentation_service, '_detect_single_characters_torchscript') as mock_torch:
            mock_torch.return_value = []

            segmentation_service._detect_single_characters_rga_crnn(sample_image, params, mock_model)

            mock_torch.assert_called_once_with(sample_image, params, mock_model)
