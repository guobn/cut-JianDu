# Recognition 页面前后端实现详细报告

## 一、项目整体架构

```
D:\project\gratuate
├── front/                 # Vue.js 前端项目
│   └── src/
│       ├── views/         # 页面组件
│       ├── api/           # API 调用模块
│       ├── store/         # Pinia 状态管理
│       ├── components/    # 可复用组件
│       ├── config/        # 配置文件
│       ├── router/        # 路由配置
│       └── utils/         # 工具函数
├── backend/               # FastAPI 后端项目
│   └── app/
│       ├── api/           # API 路由层
│       ├── services/      # 业务逻辑层
│       ├── models/        # 数据模型
│       ├── routers/       # 路由
│       ├── core/          # 核心功能
│       ├── utils/         # 工具函数
│       └── main.py        # 应用入口
```

---

## 二、前端实现 (Recognition)

### 2.1 路由配置
**文件**: `D:\project\gratuate\front\src\router\index.js`

```javascript
// Recognition 页面路由
{
  path: 'recognition',
  name: 'Recognition',
  meta: { title: '图像预处理（旋转与归一化）' },
  component: () => import('@/views/Recognition.vue')
},
{
  path: 'recognition/verify/:groupId/:stage',
  name: 'RecognitionVerify',
  meta: { title: '校验视图' },
  component: () => import('@/views/RecognitionVerifyView.vue')
}
```

### 2.2 主页面组件
**文件**: `D:\project\gratuate\front\src\views\Recognition.vue`

**功能**:
- 图像上传与选择
- 旋转校正（支持快速/异步两种模式）
- 尺寸归一化
- 图像预览与处理结果展示

**关键状态**:
```javascript
const rotationDetection = ref(null)      // 旋转检测结果
const rotationResult = ref(null)         // 旋转校正结果
const normalizationResult = ref(null)     // 归一化结果
const useFastDetection = ref(false)      // 快速检测模式开关
const normalizeParams = ref({            // 归一化参数
  target_width: 800,
  target_height: 1200,
  keep_aspect_ratio: true,
  padding_color: 'white'
})
```

**核心方法**:
- `handleDetectAngle()` - 检测倾斜角度
- `handleApplyRotation()` - 执行旋转校正
- `handleNormalize()` - 执行尺寸归一化
- `handleSelectUploadedImage()` - 选择已上传图像

### 2.3 校验视图组件
**文件**: `D:\project\gratuate\front\src\views\RecognitionVerifyView.vue`

**功能**:
- 图片列表浏览
- Canvas 框选与编辑
- 拖拽、缩放检测框
- 标记校验状态

---

## 三、前端 API 调用层

### 3.1 Recognition API（批量检测）
**文件**: `D:\project\gratuate\front\src\api\recognition.js`

```javascript
const recognitionAPI = {
  // 批量检测单支简牍
  batchDetectSlips(groupId) {
    return apiClient.post('/api/recognition/batch-detect-slips', { group_id: groupId })
  },
  // 批量检测单字符
  batchDetectChars(groupId) {
    return apiClient.post('/api/recognition/batch-detect-chars', { group_id: groupId })
  }
}
```

### 3.2 Image Processing API（图像处理）
**文件**: `D:\project\gratuate\front\src\api\imageProcessing.js`

| 方法 | 功能 | API端点 |
|------|------|---------|
| `uploadImage()` | 上传图像 | POST `/api/images/upload` |
| `detectRegions()` | 区域检测（异步） | POST `/api/segmentation/detect` |
| `detectRegionsFast()` | 区域检测（同步） | POST `/api/segmentation/detect-fast` |
| `cutImage()` | 执行切割 | POST `/api/segmentation/cut` |
| `detectRotationAngle()` | 检测旋转角度（异步） | POST `/api/rotation/detect-angle` |
| `detectRotationAngleFast()` | 检测旋转角度（同步） | POST `/api/rotation/detect-angle-fast` |
| `correctRotation()` | 旋转校正（异步） | POST `/api/rotation/correct` |
| `correctRotationFast()` | 旋转校正（同步） | POST `/api/rotation/correct-fast` |
| `normalizeSize()` | 尺寸归一化 | POST `/api/normalization/normalize` |

**超时配置**:
```javascript
const TIMEOUT_CONFIG = {
  detect: 60000,        // 检测区域：60秒
  cut: 120000,          // 切割：120秒
  rotation: 90000,      // 旋转检测：90秒
  normalization: 60000, // 尺寸归一化：60秒
  batch: 300000,         // 批量处理：300秒
  export: 600000        // 导出：600秒
}
```

---

## 四、前端状态管理

**文件**: `D:\project\gratuate\front\src\store\imageProcessing.js`

```javascript
export const useImageProcessingStore = defineStore('imageProcessing', () => {
  // 状态
  const currentImage = ref(null)      // 当前图像
  const imageUrl = ref(null)          // 图像URL
  const detectionResults = ref(null)   // 检测结果
  const segmentationResults = ref(null) // 切割结果
  const rotationResults = ref(null)   // 旋转结果
  const normalizationResults = ref(null) // 归一化结果

  // 操作
  uploadImage(),           // 上传图像
  detectSlips(),           // 检测单支（异步）
  detectSlipsFast(),       // 检测单支（同步）
  detectCharacters(),       // 检测单字符
  detectRotationAngle(),   // 检测旋转角度
  detectRotationAngleFast(), // 快速检测角度
  correctRotation(),       // 旋转校正（异步）
  correctRotationFast(),   // 旋转校正（同步）
  normalizeSize()          // 尺寸归一化
})
```

---

## 五、前端配置

**文件**: `D:\project\gratuate\front\src\config\engineParams.js`

**检测引擎**:
```javascript
// 单支检测引擎
export const SLIP_DETECT_ENGINES = [
  { value: 'yolov8', label: 'YOLOv8 (Baseline)' },
  { value: 'yolov11-finetuned', label: 'YOLOv11 微调模型' }
]

// 单字检测引擎
export const CHARACTER_DETECT_ENGINES = [
  { value: 'yolov8', label: 'YOLOv8 (Baseline)' },
  { value: 'aps-yolo', label: 'APS-YOLO (Small Objects)' },
  { value: 'deconv-yolo', label: 'DeConv-YOLO (Deformable)' },
  { value: 'rga-crnn', label: 'RGA-CRNN (Character Recognition)' },
  { value: 'yolov12', label: 'YOLOv12 (Latest)' }
]
```

**旋转引擎参数**:
```javascript
export const ROTATION_ENGINE_PARAMS = {
  min_angle: -45,
  max_angle: 45,
  angle_step: 0.5,
  default_auto_crop: true
}
```

**归一化引擎参数**:
```javascript
export const NORMALIZATION_ENGINE_PARAMS = {
  default_target_width: 800,
  default_target_height: 1200,
  min_size: 100,
  max_size: 3000,
  size_step: 50,
  default_keep_aspect_ratio: true,
  default_padding_color: 'white',
  supported_padding_colors: ['white', 'black'],
  default_interpolation: 'linear'
}
```

---

## 六、后端实现

### 6.1 API 路由注册
**文件**: `D:\project\gratuate\backend\app\main.py`

```python
from app.api import images, segmentation, rotation, normalization, metadata, tasks, recognition

app.include_router(segmentation.router)    # 切割检测路由
app.include_router(rotation.router)       # 旋转校正路由
app.include_router(normalization.router)   # 尺寸归一化路由
app.include_router(recognition.router)     # 批量检测路由
```

### 6.2 Recognition 批量检测 API
**文件**: `D:\project\gratuate\backend\app\api\recognition.py`

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/recognition/batch-detect-slips` | 批量检测单支简牍 |
| POST | `/api/recognition/batch-detect-chars` | 批量检测单字符 |

**请求/响应模型**:
```python
class BatchDetectRequest(BaseModel):
    group_id: str

class BatchDetectResponse(BaseModel):
    task_id: str        # Celery任务ID
    group_id: str       # 图像组ID
    total_images: int   # 图像总数
    status: str         # 任务状态
```

### 6.3 Segmentation API
**文件**: `D:\project\gratuate\backend\app\api\segmentation.py`

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/segmentation/detect` | 异步区域检测 |
| POST | `/api/segmentation/detect-upload` | 测试用上传检测 |
| POST | `/api/segmentation/detect-fast` | 同步快速检测 |
| POST | `/api/segmentation/cut` | 执行图像切割 |
| GET | `/api/segmentation/models` | 列出可用模型 |
| POST | `/api/segmentation/models/{model_type}/load` | 预加载模型 |

### 6.4 Rotation API
**文件**: `D:\project\gratuate\backend\app\api\rotation.py`

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/rotation/detect-angle` | 异步检测旋转角度 |
| POST | `/api/rotation/correct` | 异步执行旋转校正 |
| POST | `/api/rotation/detect-angle-fast` | 同步检测角度 |
| POST | `/api/rotation/correct-fast` | 同步执行校正 |

### 6.5 Normalization API
**文件**: `D:\project\gratuate\backend\app\api\normalization.py`

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/normalization/normalize` | 执行尺寸归一化 |

---

## 七、后端服务层

### 7.1 Celery 异步任务
**文件**: `D:\project\gratuate\backend\app\services\celery_tasks.py`

| 任务名 | 功能 |
|--------|------|
| `detect_single_slips_task` | 异步检测单支简牍 |
| `detect_single_characters_task` | 异步检测单字符 |
| `detect_rotation_angle_task` | 异步检测旋转角度 |
| `correct_rotation_task` | 异步执行旋转校正 |
| `batch_segment_slips_task` | 批量检测单支 |
| `batch_segment_chars_task` | 批量检测单字符 |

### 7.2 SegmentationService
**文件**: `D:\project\gratuate\backend\app\services\segmentation_service.py`

**主要方法**:
- `detect_single_slips()` - 单支检测
- `detect_single_characters()` - 单字符检测
- `extract_regions()` - 区域提取
- `save_segmented_regions()` - 保存切割结果

### 7.3 RotationService
**文件**: `D:\project\gratuate\backend\app\services\rotation_service.py`

**主要方法**:
- `detect_rotation_angle()` - 角度检测
- `correct_rotation()` - 旋转校正

### 7.4 NormalizationService
**文件**: `D:\project\gratuate\backend\app\services\normalization_service.py`

**主要方法**:
- `normalize_size()` - 尺寸归一化

---

## 八、数据模型

**文件**: `D:\project\gratuate\backend\app\models\detection.py`

```python
class ModelType(str, Enum):
    YOLOV8 = "yolov8"
    YOLOV11_FINETUNED = "yolov11-finetuned"

class BoundingBox(BaseModel):
    id: str
    x: int
    y: int
    width: int
    height: int
    confidence: Optional[float] = None
    rotation: float = 0.0
    order: int

class DetectionParameters(BaseModel):
    min_width: int = 50
    min_height: int = 200
    model_type: ModelType = ModelType.YOLOV8
    confidence_threshold: Optional[float] = None

class DetectionResult(BaseModel):
    detection_id: str
    image_id: str
    mode: str  # "single-slip" 或 "single-character"
    detections: List[BoundingBox]
    total_count: int
    processing_time: float
```

---

## 九、关键文件路径汇总

### 前端文件
| 文件路径 | 说明 |
|----------|------|
| `D:\project\gratuate\front\src\views\Recognition.vue` | Recognition主页面 |
| `D:\project\gratuate\front\src\views\RecognitionVerifyView.vue` | 校验视图页面 |
| `D:\project\gratuate\front\src\api\recognition.js` | Recognition API |
| `D:\project\gratuate\front\src\api\imageProcessing.js` | 图像处理API |
| `D:\project\gratuate\front\src\store\imageProcessing.js` | 状态管理 |
| `D:\project\gratuate\front\src\router\index.js` | 路由配置 |
| `D:\project\gratuate\front\src\config\engineParams.js` | 引擎参数配置 |

### 后端文件
| 文件路径 | 说明 |
|----------|------|
| `D:\project\gratuate\backend\app\api\recognition.py` | Recognition API路由 |
| `D:\project\gratuate\backend\app\api\segmentation.py` | 切割检测API |
| `D:\project\gratuate\backend\app\api\rotation.py` | 旋转校正API |
| `D:\project\gratuate\backend\app\api\normalization.py` | 归一化API |
| `D:\project\gratuate\backend\app\services\celery_tasks.py` | Celery异步任务 |
| `D:\project\gratuate\backend\app\services\segmentation_service.py` | 切割服务 |
| `D:\project\gratuate\backend\app\services\rotation_service.py` | 旋转服务 |
| `D:\project\gratuate\backend\app\services\normalization_service.py` | 归一化服务 |
| `D:\project\gratuate\backend\app\models\detection.py` | 检测数据模型 |
| `D:\project\gratuate\backend\app\main.py` | 应用入口 |

---

## 十、通信流程图

```
前端 (Vue.js)                    后端 (FastAPI)
     │                                 │
     │  POST /api/rotation/detect-angle-fast
     │  ─────────────────────────────────────>
     │                                 │
     │                           RotationService.detect_rotation_angle()
     │                           RotationService.correct_rotation()
     │                                 │
     │  { angle, confidence }           │
     │  <─────────────────────────────────────
     │                                 │
     │  POST /api/normalization/normalize
     │  ─────────────────────────────────────>
     │                                 │
     │                           NormalizationService.normalize_size()
     │                           ImageProcessor.save_image()
     │                                 │
     │  { normalization_id, output_path }
     │  <─────────────────────────────────────
     │
     ▼
 显示处理结果
```

---

## 十一、技术栈总结

### 前端技术栈
- **框架**: Vue.js 3 (Composition API)
- **状态管理**: Pinia
- **HTTP 客户端**: Axios
- **路由**: Vue Router
- **构建工具**: Vite

### 后端技术栈
- **框架**: FastAPI
- **异步任务**: Celery + Redis
- **图像处理**: OpenCV, Pillow
- **深度学习**: Ultralytics (YOLO), PyTorch
- **数据验证**: Pydantic

---

*报告生成时间: 2026-04-06*
