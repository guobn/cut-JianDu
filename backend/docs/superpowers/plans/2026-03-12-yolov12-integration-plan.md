# YOLOv12 Integration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate official YOLOv12 as an independent detection model option for single-slip detection with full backend and frontend support.

**Architecture:** Extend existing ModelFactory pattern with YOLOv12 loader, add ModelType enum value, configure model path and thresholds, integrate into frontend model selector. The existing `_detect_single_slips_yolo` method requires no modification as it uses the generic `model.predict()` API.

**Tech Stack:** Python 3.9+, FastAPI, ultralytics (YOLOv12), Vue 3 + Pinia

---

## Chunk 1: Backend Implementation (Tasks 1-4)

### Task 1: Add YOLOV12 to ModelType Enum

**Files:**
- Modify: `backend/app/models/detection.py:7-12`
- Modify: `backend/tests/models/test_detection_models.py`

- [ ] **Step 1: Add failing test**

Add to `backend/tests/models/test_detection_models.py`:
```python
def test_model_type_yolov12():
    """Test YOLOV12 enum value"""
    assert ModelType.YOLOV12.value == "yolov12"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/models/test_detection_models.py::test_model_type_yolov12 -v`
Expected: FAIL with "AttributeError: type object 'ModelType' has no attribute 'YOLOV12'"

- [ ] **Step 3: Add YOLOV12 to ModelType enum**

Modify `backend/app/models/detection.py`:
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

- [ ] **Step 1: Add YOLOv12 config to Settings class**

Modify `backend/app/config.py`, add after existing model configs:
```python
# YOLOv12 Configuration
yolov12_slip_model_path: Optional[str] = "models/yolov12n.pt"
yolov12_conf_threshold: float = Field(default=0.25, ge=0, le=1)
yolov12_class_id: int = Field(default=0, ge=0)
```

- [ ] **Step 2: Add to .env.example**

Modify `backend/.env.example`, add:
```bash
# YOLOv12 Configuration
YOLOV12_SLIP_MODEL_PATH=models/yolov12n.pt
YOLOV12_CONF_THRESHOLD=0.25
YOLOV12_CLASS_ID=0
```

- [ ] **Step 3: Verify config loads**

Run: `cd backend && python -c "from app.config import settings; print(settings.yolov12_slip_model_path)"`
Expected: `models/yolov12n.pt`

- [ ] **Step 4: Commit**

```bash
git add backend/app/config.py backend/.env.example
git commit -m "feat: add YOLOv12 configuration settings"
```

---

### Task 3: Implement ModelFactory YOLOv12 Loader

**Files:**
- Modify: `backend/app/services/model_factory.py`
- Create: `backend/tests/services/test_yolov12_integration.py`

- [ ] **Step 1: Add _load_yolov12 method**

Modify `backend/app/services/model_factory.py`, add after `_load_rga_crnn`:
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

- [ ] **Step 2: Register YOLOV12 in _load_model loaders dict**

Modify `_load_model` method:
```python
def _load_model(self, model_type: ModelType) -> Optional[Any]:
    loaders = {
        ModelType.YOLOV8: self._load_yolov8,
        ModelType.APS_YOLO: self._load_aps_yolo,
        ModelType.DECONV_YOLO: self._load_deconv_yolo,
        ModelType.RGA_CRNN: self._load_rga_crnn,
        ModelType.YOLOV12: self._load_yolov12,  # Add this line
    }
```

- [ ] **Step 3: Update fallback chain**

Modify `get_model` method fallback_order:
```python
fallback_order = [
    ModelType.YOLOV12,  # Prefer newest as fallback
    ModelType.DECONV_YOLO,
    ModelType.APS_YOLO,
    ModelType.YOLOV8,
]
```

- [ ] **Step 4: Update get_model_info path_attr_map**

Modify `get_model_info`:
```python
path_attr_map = {
    ModelType.YOLOV8: "yolov8_slip_model_path",
    ModelType.APS_YOLO: "aps_yolo_model_path",
    ModelType.DECONV_YOLO: "deconv_yolo_model_path",
    ModelType.RGA_CRNN: "rga_crnn_model_path",
    ModelType.YOLOV12: "yolov12_slip_model_path",  # Add this line
}
```

- [ ] **Step 5: Create integration test file**

Create `backend/tests/services/test_yolov12_integration.py`:
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

- [ ] **Step 6: Run all ModelFactory tests**

Run: `pytest backend/tests/services/test_model_factory.py backend/tests/services/test_yolov12_integration.py -v`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/model_factory.py backend/tests/services/test_yolov12_integration.py
git commit -m "feat: implement ModelFactory YOLOv12 loader with fallback"
```

---

### Task 4: Verify API Endpoints

**Files:**
- Verify: `backend/app/api/segmentation.py`

- [ ] **Step 1: Verify /models endpoint auto-includes YOLOv12**

The endpoint at line 393-413 iterates over all ModelType values:
```python
@router.get("/models")
async def list_models():
    from app.services.model_factory import get_model_factory
    factory = get_model_factory()
    models = {}
    for model_type in ModelType:  # Automatically includes YOLOV12
        info = factory.get_model_info(model_type)
        models[model_type.value] = info
```

No code change needed - verify by reading the code.

- [ ] **Step 2: Update README.md**

Modify `backend/README.md`, add YOLOv12 to models list:
```markdown
## Available Models

- **YOLOv8**: Baseline model for slip detection
- **APS-YOLO**: Adaptive Pyramid Sampling for small objects
- **DeConv-YOLO**: Deformable Convolution for shape adaptation
- **RGA-CRNN**: Rotated Glyph Attention for character recognition
- **YOLOv12**: Latest official model with improved attention (NEW)
```

- [ ] **Step 3: Commit**

```bash
git add backend/README.md
git commit -m "docs: document YOLOv12 model support"
```

---

## Chunk 2: Frontend Implementation (Tasks 5-6)

### Task 5: Update Frontend Pinia Store

**Files:**
- Modify: `front/src/store/imageProcessing.js`
- Test: `front/src/store/__tests__/imageProcessing.test.js`

- [ ] **Step 1: Add YOLOv12 test cases**

Add to `front/src/store/__tests__/imageProcessing.test.js`:
```javascript
it('should include YOLOv12 in availableEngines', () => {
  expect(store.availableEngines).toEqual([
    { value: 'yolov8', label: 'YOLOv8 (Baseline)' },
    { value: 'aps-yolo', label: 'APS-YOLO (Small Objects)' },
    { value: 'deconv-yolo', label: 'DeConv-YOLO (Deformable)' },
    { value: 'rga-crnn', label: 'RGA-CRNN (Character Recognition)' },
    { value: 'yolov12', label: 'YOLOv12 (Latest)' }
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
Expected: FAIL - YOLOv12 not in availableEngines

- [ ] **Step 3: Update availableEngines**

Modify `front/src/store/imageProcessing.js`:
```javascript
const availableEngines = ref([
  { value: 'yolov8', label: 'YOLOv8 (Baseline)' },
  { value: 'aps-yolo', label: 'APS-YOLO (Small Objects)' },
  { value: 'deconv-yolo', label: 'DeConv-YOLO (Deformable)' },
  { value: 'rga-crnn', label: 'RGA-CRNN (Character Recognition)' },
  { value: 'yolov12', label: 'YOLOv12 (Latest)' }  // Add this line
])
```

- [ ] **Step 4: Add YOLOv12 to engineParams map**

Modify `front/src/store/imageProcessing.js`:
```javascript
const engineParams = computed(() => (engineType) => {
  const paramsMap = {
    'yolov8': { slice_size: 640, overlap_ratio: 0.25, use_soft_nms: true },
    'aps-yolo': { slice_size: 640, overlap_ratio: 0.4, use_soft_nms: true },
    'deconv-yolo': { slice_size: 640, overlap_ratio: 0.25, use_soft_nms: true },
    'rga-crnn': { slice_size: 512, overlap_ratio: 0.35, use_soft_nms: true },
    'yolov12': { slice_size: 640, overlap_ratio: 0.25, use_soft_nms: true }  // Add this line
  }
  return paramsMap[engineType] || paramsMap['yolov8']
})
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd front && npm test -- imageProcessing.test.js`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add front/src/store/imageProcessing.js front/src/store/__tests__/imageProcessing.test.js
git commit -m "feat: add YOLOv12 to Pinia store"
```

---

### Task 6: Update ModelSelector Component

**Files:**
- Modify: `front/src/components/ModelSelector.vue`

- [ ] **Step 1: Add YOLOv12 description**

Modify `front/src/components/ModelSelector.vue`:
```javascript
const descriptions = computed(() => {
  const descriptions = {
    'yolov8': 'YOLOv8 是基线模型，适用于常规的目标检测任务，平衡速度和精度',
    'aps-yolo': 'APS-YOLO 使用自适应特征金字塔，专门针对小目标检测优化，适合检测细小的文字',
    'deconv-yolo': 'DeConv-YOLO 使用可变形卷积，更好地适应不同形状的物体，提高检测鲁棒性',
    'rga-crnn': 'RGA-CRNN 专门用于文字识别，支持旋转文字和弯曲文本的检测',
    'yolov12': 'YOLOv12 是最新官方模型，使用改进的注意力机制，提供更高的检测精度'  // Add this line
  }
  return props.showDescription ? descriptions[selectedEngine.value] : null
})
```

- [ ] **Step 2: Update getEngineDescription**

```javascript
function getEngineDescription(engineType) {
  const descMap = {
    'yolov8': '基线模型，平衡速度与精度',
    'aps-yolo': '小目标检测优化',
    'deconv-yolo': '可变形卷积增强',
    'rga-crnn': '文字识别专用',
    'yolov12': '最新官方模型，更高精度'  // Add this line
  }
  return descMap[engineType] || ''
}
```

- [ ] **Step 3: Verify component renders YOLOv12 option**

The el-select iterates over `availableEngines` from the store, which now includes YOLOv12.

- [ ] **Step 4: Commit**

```bash
git add front/src/components/ModelSelector.vue
git commit -m "feat: add YOLOv12 to ModelSelector component"
```

---

## Chunk 3: Testing and Verification (Tasks 7-8)

### Task 7: Manual Testing

**Files:**
- Test: Backend API and Frontend UI

- [ ] **Step 1: Start backend server**

Run: `cd backend && uvicorn app.main:app --reload`
Expected: Server starts on http://127.0.0.1:8000

- [ ] **Step 2: Test /api/segmentation/models endpoint**

Run: `curl http://127.0.0.1:8000/api/segmentation/models`
Expected: Response includes `"yolov12": {"available": false, "path": "models/yolov12n.pt", ...}`

- [ ] **Step 3: Start frontend dev server**

Run: `cd front && npm run dev`
Expected: Server starts

- [ ] **Step 4: Verify YOLOv12 appears in model selector**

Open browser to frontend, navigate to Segmentation page.
Expected: ModelSelector dropdown shows "YOLOv12 (Latest)" option

- [ ] **Step 5: Select YOLOv12 and verify params**

In browser console, check store state.
Expected: `engineParams('yolov12')` returns `{ slice_size: 640, overlap_ratio: 0.25, use_soft_nms: true }`

---

### Task 8: Final Verification

- [ ] **Step 1: Run all backend tests**

Run: `pytest backend/tests/ -v`
Expected: All tests pass including YOLOv12 tests

- [ ] **Step 2: Run all frontend tests**

Run: `cd front && npm test`
Expected: All tests pass including YOLOv12 tests

- [ ] **Step 3: Verify no breaking changes**

Run: `pytest backend/tests/services/test_segmentation_model_factory.py -v`
Expected: All existing tests still pass

- [ ] **Step 4: Create git tag**

Run: `git tag -a v1.1.0-yolov12 -m "YOLOv12 Integration"`
Expected: Tag created

---

## Success Criteria

- [ ] ModelType.YOLOV12 enum value exists
- [ ] ModelFactory can load YOLOv12 model
- [ ] Fallback chain includes YOLOv12
- [ ] Frontend store includes YOLOv12 in availableEngines
- [ ] ModelSelector component displays YOLOv12 option
- [ ] /api/segmentation/models endpoint returns YOLOv12 status
- [ ] All 10+ automated tests pass
- [ ] No breaking changes to existing functionality
