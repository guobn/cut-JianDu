# YOLOv12 Integration for Slip Detection

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate official YOLOv12 as an independent detection model option for single-slip detection, with full ModelFactory support and frontend model selector integration.

**Architecture:** Extend existing ModelFactory pattern with YOLOv12 loader, add ModelType enum value, configure model path and thresholds, integrate into frontend model selector. The existing `_detect_single_slips_yolo` method requires no modification as it uses the generic `model.predict()` API.

**Tech Stack:** Python 3.9+, FastAPI, ultralytics (YOLOv12), Vue 3 + Pinia

---

## Files to Modify

### Backend Files
- **Modify:** `backend/app/models/detection.py` - Add YOLOV12 enum value
- **Modify:** `backend/app/services/model_factory.py` - Add _load_yolov12 method and registration
- **Modify:** `backend/app/config.py` - Add YOLOv12 configuration settings
- **Modify:** `backend/.env.example` - Add YOLOv12 environment variable examples

### Frontend Files
- **Modify:** `front/src/store/imageProcessing.js` - Add YOLOv12 to availableEngines and params map
- **Modify:** `front/src/components/ModelSelector.vue` - Add YOLOv12 option display

### Test Files
- **Create:** `backend/tests/services/test_yolov12_integration.py` - YOLOv12 specific tests
- **Modify:** `backend/tests/models/test_detection_models.py` - Add YOLOV12 enum test

---

## Implementation Tasks

### Task 1: Add YOLOV12 to ModelType Enum

**Files:**
- Modify: `backend/app/models/detection.py:7-12`

- [ ] **Step 1: Write the failing test**

Add test for YOLOV12 enum value in `backend/tests/models/test_detection_models.py`:
```python
def test_model_type_yolov12():
    assert ModelType.YOLOV12.value == "yolov12"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/models/test_detection_models.py::test_model_type_yolov12 -v`
Expected: FAIL with "AttributeError: YOLOV12"

- [ ] **Step 3: Add YOLOV12 to ModelType enum**

```python
class ModelType(str, Enum):
    """Detection model types"""
    YOLOV8 = "yolov8"
    APS_YOLO = "aps-yolo"
    DECONV_YOLO = "deconv-yolo"
    RGA_CRNN = "rga-crnn"
    YOLOV12 = "yolov12"  # YOLOv12 baseline
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/models/test_detection_models.py::test_model_type_yolov12 -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/detection.py backend/tests/models/test_detection_models.py
git commit -m "feat: add YOLOV12 to ModelType enum"
```

---

### Task 2: Add YOLOv12 Configuration

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`

- [ ] **Step 1: Write failing test for config values**

Create simple test to verify config can be loaded:
```python
def test_yolov12_config():
    assert hasattr(settings, 'yolov12_slip_model_path')
    assert hasattr(settings, 'yolov12_conf_threshold')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/config/test_config.py::test_yolov12_config -v`
Expected: FAIL

- [ ] **Step 3: Add YOLOv12 config to Settings class**

In `backend/app/config.py`:
```python
# YOLOv12 Configuration
yolov12_slip_model_path: Optional[str] = "models/yolov12n.pt"
yolov12_conf_threshold: float = Field(default=0.25, ge=0, le=1)
yolov12_class_id: int = Field(default=0, ge=0)
```

- [ ] **Step 4: Add to .env.example**

```bash
# YOLOv12 Configuration
YOLOV12_SLIP_MODEL_PATH=models/yolov12n.pt
YOLOV12_CONF_THRESHOLD=0.25
YOLOV12_CLASS_ID=0
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest backend/tests/config/test_config.py::test_yolov12_config -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/.env.example
git commit -m "feat: add YOLOv12 configuration settings"
```

---

### Task 3: Implement ModelFactory YOLOv12 Loader

**Files:**
- Modify: `backend/app/services/model_factory.py`

- [ ] **Step 1: Write failing test for YOLOv12 loading**

```python
def test_load_yolov12_model():
    factory = ModelFactory()
    with patch('app.services.model_factory.settings') as mock_settings:
        mock_settings.yolov12_slip_model_path = "/fake/path.pt"
        with patch.object(factory, '_load_yolov12') as mock_load:
            mock_model = Mock()
            mock_load.return_value = mock_model
            model = factory.get_model(ModelType.YOLOV12, use_fallback=False)
            assert model is mock_model
            mock_load.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/services/test_model_factory.py::test_load_yolov12_model -v`
Expected: FAIL with "Unsupported model type"

- [ ] **Step 3: Add _load_yolov12 method**

```python
def _load_yolov12(self) -> Optional[Any]:
    """
    Load YOLOv12 model (Official YOLOv12 baseline)

    YOLOv12 uses improved attention mechanisms for better accuracy
    Config: YOLOV12_SLIP_MODEL_PATH in settings
    """
    if not _YOLO_AVAILABLE:
        return None

    model_path = getattr(settings, "yolov12_slip_model_path", None)
    if not model_path:
        return None

    path = self._resolve_model_path(model_path)
    if not path.exists():
        self._logger.warning("YOLOv12 model file not found: %s", path)
        return None

    try:
        model = YOLO(str(path))
        self._logger.info("YOLOv12 model loaded: %s", path)
        return model
    except Exception as e:
        self._logger.warning("YOLOv12 load failed: %s", e)
        return None
```

- [ ] **Step 4: Register YOLOv12 in loaders dict**

```python
def _load_model(self, model_type: ModelType) -> Optional[Any]:
    loaders = {
        ModelType.YOLOV8: self._load_yolov8,
        ModelType.APS_YOLO: self._load_aps_yolo,
        ModelType.DECONV_YOLO: self._load_deconv_yolo,
        ModelType.RGA_CRNN: self._load_rga_crnn,
        ModelType.YOLOV12: self._load_yolov12,  # Add this
    }
```

- [ ] **Step 5: Update fallback chain to include YOLOv12**

```python
fallback_order = [
    ModelType.YOLOV12,  # Prefer newest as fallback
    ModelType.DECONV_YOLO,
    ModelType.APS_YOLO,
    ModelType.YOLOV8,
]
```

- [ ] **Step 6: Update get_model_info path_attr_map**

```python
path_attr_map = {
    ModelType.YOLOV8: "yolov8_slip_model_path",
    ModelType.APS_YOLO: "aps_yolo_model_path",
    ModelType.DECONV_YOLO: "deconv_yolo_model_path",
    ModelType.RGA_CRNN: "rga_crnn_model_path",
    ModelType.YOLOV12: "yolov12_slip_model_path",  # Add this
}
```

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest backend/tests/services/test_model_factory.py -v`
Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/model_factory.py
git commit -m "feat: implement ModelFactory YOLOv12 loader with fallback"
```

---

### Task 4: Create YOLOv12 Integration Tests

**Files:**
- Create: `backend/tests/services/test_yolov12_integration.py`

- [ ] **Step 1: Write comprehensive YOLOv12 tests**

```python
"""Tests for YOLOv12 integration"""
import pytest
from unittest.mock import Mock, patch
from app.services.model_factory import ModelFactory
from app.models.detection import ModelType


class TestYOLOv12Integration:
    """Test YOLOv12 model integration"""

    def test_yolov12_enum_value(self):
        assert ModelType.YOLOV12.value == "yolov12"

    def test_yolov12_not_configured_returns_none(self):
        factory = ModelFactory()
        with patch('app.services.model_factory.settings') as mock_settings:
            mock_settings.yolov12_slip_model_path = None
            model = factory.get_model(ModelType.YOLOV12, use_fallback=False)
            assert model is None

    def test_yolov12_model_file_not_exists_returns_none(self):
        factory = ModelFactory()
        with patch('app.services.model_factory.settings') as mock_settings:
            mock_settings.yolov12_slip_model_path = "/nonexistent/yolov12.pt"
            model = factory.get_model(ModelType.YOLOV12, use_fallback=False)
            assert model is None

    def test_yolov12_caches_loaded_model(self):
        factory = ModelFactory()
        with patch('app.services.model_factory.settings') as mock_settings:
            mock_settings.yolov12_slip_model_path = "/fake/yolov12.pt"
            with patch.object(factory, '_load_yolov12') as mock_load:
                mock_model = Mock()
                mock_load.return_value = mock_model

                factory.get_model(ModelType.YOLOV12, use_fallback=False)
                factory.get_model(ModelType.YOLOV12, use_fallback=False)

                mock_load.assert_called_once()

    def test_yolov12_fallback_to_yolov8(self):
        factory = ModelFactory()
        with patch('app.services.model_factory.settings') as mock_settings:
            mock_settings.yolov12_slip_model_path = None  # YOLOv12 unavailable
            mock_settings.yolov8_slip_model_path = "/fake/yolov8.pt"

            with patch.object(factory, '_load_yolov8') as mock_load_yolo8:
                mock_model = Mock()
                mock_load_yolo8.return_value = mock_model

                model = factory.get_model(ModelType.YOLOV12, use_fallback=True)
                assert model is mock_model
                mock_load_yolo8.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest backend/tests/services/test_yolov12_integration.py -v`
Expected: All 5 tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/tests/services/test_yolov12_integration.py
git commit -m "test: add YOLOv12 integration tests"
```

---

### Task 5: Update Frontend Store

**Files:**
- Modify: `front/src/store/imageProcessing.js`
- Modify: `front/src/components/ModelSelector.vue`

- [ ] **Step 1: Write failing test for frontend store**

```javascript
it('should include YOLOv12 in availableEngines', () => {
  expect(store.availableEngines).toEqual([
    { value: 'yolov8', label: 'YOLOv8 (Baseline)' },
    { value: 'aps-yolo', label: 'APS-YOLO (Small Objects)' },
    { value: 'deconv-yolo', label: 'DeConv-YOLO (Deformable)' },
    { value: 'rga-crnn', label: 'RGA-CRNN (Character Recognition)' },
    { value: 'yolov12', label: 'YOLOv12 (Latest)' }  // Add this
  ])
})

it('should return YOLOv12 specific SAHI parameters', () => {
  const params = store.getEngineParams('yolov12')
  expect(params).toEqual({
    slice_size: 640,
    overlap_ratio: 0.25,
    use_soft_nms: true
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd front && npm test -- imageProcessing.test.js`
Expected: FAIL

- [ ] **Step 3: Update availableEngines in imageProcessing.js**

```javascript
const availableEngines = ref([
  { value: 'yolov8', label: 'YOLOv8 (Baseline)' },
  { value: 'aps-yolo', label: 'APS-YOLO (Small Objects)' },
  { value: 'deconv-yolo', label: 'DeConv-YOLO (Deformable)' },
  { value: 'rga-crnn', label: 'RGA-CRNN (Character Recognition)' },
  { value: 'yolov12', label: 'YOLOv12 (Latest)' }  // Add this
])
```

- [ ] **Step 4: Add YOLOv12 to engineParams map**

```javascript
const paramsMap = {
  'yolov8': { slice_size: 640, overlap_ratio: 0.25, use_soft_nms: true },
  'aps-yolo': { slice_size: 640, overlap_ratio: 0.4, use_soft_nms: true },
  'deconv-yolo': { slice_size: 640, overlap_ratio: 0.25, use_soft_nms: true },
  'rga-crnn': { slice_size: 512, overlap_ratio: 0.35, use_soft_nms: true },
  'yolov12': { slice_size: 640, overlap_ratio: 0.25, use_soft_nms: true }  // Add this
}
```

- [ ] **Step 5: Update ModelSelector.vue description**

```javascript
const descriptions = {
  'yolov8': 'YOLOv8 是基线模型，适用于常规的目标检测任务，平衡速度和精度',
  'aps-yolo': 'APS-YOLO 使用自适应特征金字塔，专门针对小目标检测优化，适合检测细小的文字',
  'deconv-yolo': 'DeConv-YOLO 使用可变形卷积，更好地适应不同形状的物体，提高检测鲁棒性',
  'rga-crnn': 'RGA-CRNN 专门用于文字识别，支持旋转文字和弯曲文本的检测',
  'yolov12': 'YOLOv12 是最新官方模型，使用改进的注意力机制，提供更高的检测精度'  // Add this
}
```

- [ ] **Step 6: Update getEngineDescription**

```javascript
const descMap = {
  'yolov8': '基线模型，平衡速度与精度',
  'aps-yolo': '小目标检测优化',
  'deconv-yolo': '可变形卷积增强',
  'rga-crnn': '文字识别专用',
  'yolov12': '最新官方模型，更高精度'  // Add this
}
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd front && npm test -- imageProcessing.test.js`
Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
git add front/src/store/imageProcessing.js front/src/components/ModelSelector.vue
git commit -m "feat: add YOLOv12 to frontend model selector"
```

---

### Task 6: Update API Model Health Endpoints

**Files:**
- Modify: `backend/app/api/segmentation.py` (already handles all ModelType values dynamically)

- [ ] **Step 1: Verify /api/segmentation/models endpoint**

The endpoint iterates over all ModelType values:
```python
for model_type in ModelType:
    info = factory.get_model_info(model_type)
```

This automatically includes YOLOv12 - no code change needed.

- [ ] **Step 2: Test the endpoint manually**

Run: `curl http://localhost:8000/api/segmentation/models`
Expected: Response includes "yolov12" in models dict

- [ ] **Step 3: Document in README**

Add YOLOv12 to available models list in `backend/README.md`.

- [ ] **Step 4: Commit**

```bash
git add backend/README.md
git commit -m "docs: document YOLOv12 model support"
```

---

## Testing Strategy

1. **Unit Tests:** ModelType enum, ModelFactory loader, config values
2. **Integration Tests:** Full detection pipeline with YOLOv12
3. **Frontend Tests:** Store actions, computed properties, ModelSelector component
4. **Manual Testing:**
   - Upload test image, select YOLOv12, verify detection
   - Compare YOLOv12 vs YOLOv8 detection results
   - Test fallback when YOLOv12 model file is missing

## Success Criteria

- [ ] All 10+ automated tests pass
- [ ] YOLOv12 appears in model selector UI
- [ ] YOLOv12 can be selected and used for detection
- [ ] Fallback to YOLOv8 works when YOLOv12 unavailable
- [ ] Model health endpoint shows YOLOv12 status
- [ ] No breaking changes to existing API

## Rollback Plan

If issues arise:
1. Remove YOLOV12 from frontend availableEngines
2. Set `yolov12_slip_model_path` to null in config
3. System automatically falls back to YOLOv8
