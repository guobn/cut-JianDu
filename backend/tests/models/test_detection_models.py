"""Tests for detection models and ModelType enum"""
import pytest
from app.models.detection import ModelType, DetectionParameters


def test_model_type_enum_values():
    """Test ModelType enum values"""
    assert ModelType.YOLOV8.value == "yolov8"
    assert ModelType.APS_YOLO.value == "aps-yolo"
    assert ModelType.DECONV_YOLO.value == "deconv-yolo"
    assert ModelType.RGA_CRNN.value == "rga-crnn"


def test_model_type_is_string_enum():
    """Test ModelType is a string enum (can be compared with strings)"""
    assert ModelType.YOLOV8 == "yolov8"
    assert ModelType.APS_YOLO == "aps-yolo"


def test_detection_parameters_with_model_type():
    """Test DetectionParameters accepts model_type"""
    params = DetectionParameters(model_type=ModelType.APS_YOLO)
    assert params.model_type == ModelType.APS_YOLO


def test_detection_parameters_default_model():
    """Test default model is YOLOv8"""
    params = DetectionParameters()
    assert params.model_type == ModelType.YOLOV8


def test_detection_parameters_other_fields_unchanged():
    """Test other DetectionParameters fields are unchanged"""
    params = DetectionParameters()
    assert params.min_width == 50
    assert params.min_height == 200
    assert params.aspect_ratio_min == 0.05
    assert params.aspect_ratio_max == 0.2
    assert params.background_type == "white"


def test_detection_parameters_custom_values():
    """Test DetectionParameters accepts custom values"""
    params = DetectionParameters(
        min_width=100,
        min_height=300,
        model_type=ModelType.DECONV_YOLO
    )
    assert params.min_width == 100
    assert params.min_height == 300
    assert params.model_type == ModelType.DECONV_YOLO


def test_model_type_yolov12():
    """Test YOLOV12 enum value"""
    assert ModelType.YOLOV12.value == "yolov12"
