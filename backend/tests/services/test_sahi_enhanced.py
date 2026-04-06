"""Tests for enhanced SAHI with model-aware parameters"""
import pytest
from app.services.segmentation_service import SahiInference
from app.models.detection import ModelType


class TestSahiGetParamsForModel:
    """Test get_sahi_params_for_model method"""

    def test_get_sahi_params_yolov8(self):
        """Test SAHI parameters for YOLOv8"""
        params = SahiInference.get_sahi_params_for_model(ModelType.YOLOV8)
        assert params['slice_size'] == 640
        assert params['overlap_ratio'] == 0.25
        assert params['use_soft_nms'] is True

    def test_get_sahi_params_aps_yolo(self):
        """Test SAHI parameters for APS-YOLO - more overlap for small objects"""
        params = SahiInference.get_sahi_params_for_model(ModelType.APS_YOLO)
        assert params['slice_size'] == 640
        assert params['overlap_ratio'] == 0.4  # More overlap for small objects
        assert params['use_soft_nms'] is True

    def test_get_sahi_params_deconv_yolo(self):
        """Test SAHI parameters for DeConv-YOLO"""
        params = SahiInference.get_sahi_params_for_model(ModelType.DECONV_YOLO)
        assert params['slice_size'] == 640
        assert params['overlap_ratio'] == 0.25
        assert params['use_soft_nms'] is True

    def test_get_sahi_params_rga_crnn(self):
        """Test SAHI parameters for RGA-CRNN - smaller slices for characters"""
        params = SahiInference.get_sahi_params_for_model(ModelType.RGA_CRNN)
        assert params['slice_size'] == 512  # Smaller for characters
        assert params['overlap_ratio'] == 0.35
        assert params['use_soft_nms'] is True

    def test_get_sahi_params_default(self):
        """Test default parameters for unknown model"""
        params = SahiInference.get_sahi_params_for_model("unknown_model")
        # Should default to YOLOv8 params
        assert params['slice_size'] == 640
        assert params['overlap_ratio'] == 0.25


class TestSahiGenerateSlicesWithModelType:
    """Test generate_slices with model_type parameter"""

    def test_generate_slices_default_params(self):
        """Test slice generation with default parameters"""
        image_shape = (1000, 1000)
        slices = SahiInference.generate_slices(image_shape, slice_size=640, overlap_ratio=0.25)
        assert len(slices) > 0

    def test_generate_slices_aps_yolo_more_overlap(self):
        """Test APS-YOLO generates more slices due to higher overlap"""
        image_shape = (1000, 1000)

        # Default overlap
        slices_default = SahiInference.generate_slices(
            image_shape, slice_size=640, overlap_ratio=0.25
        )

        # APS-YOLO overlap (0.4)
        slices_aps = SahiInference.generate_slices(
            image_shape, slice_size=640, overlap_ratio=0.4
        )

        # More overlap should produce more slices
        assert len(slices_aps) >= len(slices_default)

    def test_generate_slices_small_image_no_slicing(self):
        """Test that small images return single slice"""
        image_shape = (500, 500)
        slices = SahiInference.generate_slices(image_shape, slice_size=640, overlap_ratio=0.25)
        assert len(slices) == 1
        assert slices[0].x_offset == 0
        assert slices[0].y_offset == 0


class TestSahiSoftNms:
    """Test Soft-NMS implementation"""

    def test_soft_nms_reduces_overlapping_boxes(self):
        """Test Soft-NMS handles overlapping boxes"""
        # Create overlapping boxes
        boxes = [
            (10, 10, 50, 50, 0.9),   # Box 1 - high confidence
            (15, 15, 50, 50, 0.7),   # Box 2 - overlaps with 1
            (100, 100, 50, 50, 0.8), # Box 3 - no overlap
        ]

        result = SahiInference.soft_nms(boxes, iou_threshold=0.5, score_threshold=0.3)

        # Should keep at least 2 boxes (box 3 and either 1 or 2)
        assert len(result) >= 2

    def test_soft_nms_empty_input(self):
        """Test Soft-NMS with empty input"""
        result = SahiInference.soft_nms([], iou_threshold=0.5)
        assert result == []

    def test_soft_nms_single_box(self):
        """Test Soft-NMS with single box"""
        boxes = [(10, 10, 50, 50, 0.9)]
        result = SahiInference.soft_nms(boxes, iou_threshold=0.5)
        assert len(result) == 1

    def test_soft_nms_removes_low_confidence(self):
        """Test Soft-NMS removes boxes below score threshold"""
        boxes = [
            (10, 10, 50, 50, 0.9),
            (15, 15, 50, 50, 0.1),  # Very low confidence
        ]

        result = SahiInference.soft_nms(boxes, iou_threshold=0.5, score_threshold=0.3)
        # Low confidence box should be filtered
        assert len(result) == 1


class TestSahiNms:
    """Test standard NMS implementation"""

    def test_nms_removes_overlapping_boxes(self):
        """Test NMS removes overlapping boxes"""
        boxes = [
            (10, 10, 50, 50, 0.9),   # Box 1 - high confidence
            (15, 15, 50, 50, 0.7),   # Box 2 - overlaps with 1
            (100, 100, 50, 50, 0.8), # Box 3 - no overlap
        ]

        result = SahiInference.nms(boxes, iou_threshold=0.5)

        # Should keep 2 boxes (one from overlapping pair, plus non-overlapping)
        assert len(result) == 2

    def test_nms_empty_input(self):
        """Test NMS with empty input"""
        result = SahiInference.nms([], iou_threshold=0.5)
        assert result == []
