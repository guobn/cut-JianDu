# 古文字简牍图像处理系统 - 后端

基于 FastAPI 的图像处理后端服务，提供简牍图像的切割、旋转校正和尺寸归一化功能。

## 功能特性

- ✂️ **单支简牍切割**：自动检测并切割单个简牍
- 📝 **单字切割**：检测并切割简牍上的单个文字
- 🔄 **旋转校正**：自动检测并校正图像倾斜
- 📐 **尺寸归一化**：统一图像尺寸规格

## 技术栈

- **FastAPI**: Web 框架
- **OpenCV**: 图像处理
- **NumPy**: 数值计算
- **Pillow**: 图像格式转换
- **Pydantic**: 数据验证
- **Ultralytics (YOLO 系列)**：可选，用于单支简牍检测（配置模型路径后启用）

## 可用模型

系统支持多种检测模型，可通过 `/api/segmentation/models` 端点查看实时状态：

- **YOLOv8**: 基线模型，适用于常规目标检测任务，平衡速度和精度
- **APS-YOLO**: 使用自适应特征金字塔，专门针对小目标检测优化
- **DeConv-YOLO**: 使用可变形卷积，更好地适应不同形状的物体
- **RGA-CRNN**: 专门用于文字识别，支持旋转文字和弯曲文本的检测
- **YOLOv12**: 最新官方模型，使用改进的注意力机制，提供更高的检测精度（NEW）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并根据需要修改配置：

```bash
cp .env.example .env
```

### 3. 启动服务

开发环境：
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

生产环境：
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. 单支检测使用 YOLOv8（可选）

若需使用 YOLOv8 检测单支简牍（效果更好）：

1. 将 `yolov8l.pt` 放到项目根目录下 `models/` 文件夹（可自训练或使用已导出的 2 分类模型）。
2. 在 `.env` 中配置：
   - `YOLOV8_SLIP_MODEL_PATH=models/yolov8l.pt`
   - `YOLOV8_SLIP_CLASS_ID=0`（2 分类时 0 表示单支）
   - `YOLOV8_SLIP_CONF_THRESHOLD=0.25`
3. 后端会优先用 YOLO 检测，并只保留**长条形状**（宽高比在检测参数范围内）的框；未配置或模型不存在时自动回退到 OpenCV 轮廓检测。

### 5. 访问 API 文档

启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 接口

### 图像上传

```http
POST /api/images/upload
Content-Type: multipart/form-data

file: <图像文件>
```

### 单支简牍检测

```http
POST /api/segmentation/detect
Content-Type: application/json

{
  "image_id": "img_20260204_abc123",
  "mode": "single-slip",
  "parameters": {
    "min_width": 50,
    "min_height": 200,
    "aspect_ratio_min": 0.05,
    "aspect_ratio_max": 0.2
  }
}
```

### 单字检测

```http
POST /api/segmentation/detect
Content-Type: application/json

{
  "image_id": "img_20260204_abc123",
  "mode": "single-character",
  "parameters": {
    "min_width": 20,
    "min_height": 20,
    "max_width": 150,
    "max_height": 150
  }
}
```

### 执行切割

```http
POST /api/segmentation/cut
Content-Type: application/json

{
  "image_id": "img_20260204_abc123",
  "bounding_boxes": [...],
  "output_format": "png",
  "add_padding": false,
  "padding_size": 10
}
```

### 检测旋转角度

```http
POST /api/rotation/detect-angle?image_id=img_20260204_abc123
```

### 旋转校正

```http
POST /api/rotation/correct
Content-Type: application/json

{
  "image_id": "img_20260204_abc123",
  "angle": null,
  "auto_crop": true
}
```

### 尺寸归一化

```http
POST /api/normalization/normalize
Content-Type: application/json

{
  "image_id": "img_20260204_abc123",
  "target_width": 800,
  "target_height": 1200,
  "keep_aspect_ratio": true,
  "padding_color": "white"
}
```

## 项目结构

```
app/
├── api/                    # API 路由
│   ├── images.py          # 图像上传接口
│   ├── segmentation.py    # 切割接口
│   ├── rotation.py        # 旋转校正接口
│   └── normalization.py   # 归一化接口
├── models/                # 数据模型
│   ├── image.py
│   ├── detection.py
│   ├── rotation.py
│   └── normalization.py
├── services/              # 业务逻辑
│   ├── image_service.py
│   ├── segmentation_service.py
│   ├── rotation_service.py
│   └── normalization_service.py
├── utils/                 # 工具函数
│   ├── image_utils.py
│   └── file_utils.py
├── config.py             # 配置管理
└── main.py               # 应用入口
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| APP_NAME | 应用名称 | 古文字简牍图像处理系统 |
| APP_VERSION | 应用版本 | 1.0.0 |
| DEBUG | 调试模式 | True |
| APP_HOST | 服务器地址 | 127.0.0.1 |
| APP_PORT | 服务器端口 | 8000 |
| UPLOAD_DIR | 上传目录 | ./uploads |
| RESULT_DIR | 结果目录 | ./results |
| MAX_FILE_SIZE | 最大文件大小 | 52428800 (50MB) |

## 开发指南

### 添加新的图像处理功能

1. 在 `services/` 中创建服务类
2. 在 `models/` 中定义数据模型
3. 在 `api/` 中创建路由
4. 在 `main.py` 中注册路由

### 测试

```bash
# 运行测试
pytest tests/ -v

# 查看覆盖率
pytest tests/ --cov=app
```

## 常见问题

### 1. 中文路径问题

使用 `cv2.imdecode` 而不是 `cv2.imread` 来处理中文路径。

### 2. 图像格式支持

支持 JPG、PNG、TIFF、BMP 格式。

### 3. 内存优化

对于大图像，建议先缩小再处理。

## 许可证

MIT License

## 联系方式

如有问题，请提交 Issue。
