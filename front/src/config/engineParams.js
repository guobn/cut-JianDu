/**
 * 引擎参数配置文件
 *
 * 集中管理所有图像处理引擎的参数配置
 * 包括检测、切割、旋转、归一化等引擎参数
 */

// ==================== 检测引擎参数 ====================

/**
 * 单支检测引擎列表（只包含 YOLOv8 和 YOLOv11微调）
 */
export const SLIP_DETECT_ENGINES = [
  { value: 'yolov8', label: 'YOLOv8 (Baseline)' },
  { value: 'yolov11-finetuned', label: 'YOLOv11 微调模型' }
]

/**
 * 单字检测引擎列表（保持原有配置）
 */
export const CHARACTER_DETECT_ENGINES = [
  { value: 'yolov8', label: 'YOLOv8 (Baseline)' },
  { value: 'aps-yolo', label: 'APS-YOLO (Small Objects)' },
  { value: 'deconv-yolo', label: 'DeConv-YOLO (Deformable)' },
  { value: 'rga-crnn', label: 'RGA-CRNN (Character Recognition)' },
  { value: 'yolov12', label: 'YOLOv12 (Latest)' }
]

/**
 * 可用的检测引擎列表（默认，用于兼容）
 */
export const AVAILABLE_DETECT_ENGINES = SLIP_DETECT_ENGINES

/**
 * 检测引擎默认值
 */
export const DEFAULT_DETECT_ENGINE = 'yolov8'

/**
 * 检测引擎描述信息
 */
export const DETECT_ENGINE_DESCRIPTIONS = {
  'yolov8': 'YOLOv8 是基线模型，适用于常规的目标检测任务，平衡速度和精度',
  'yolov11-finetuned': 'YOLOv11 微调模型，专门针对单支简牍检测优化，精度更高',
  'aps-yolo': 'APS-YOLO 使用自适应特征金字塔，专门针对小目标检测优化，适合检测细小的文字',
  'deconv-yolo': 'DeConv-YOLO 使用可变形卷积，更好地适应不同形状的物体，提高检测鲁棒性',
  'rga-crnn': 'RGA-CRNN 专门用于文字识别，支持旋转文字和弯曲文本的检测',
  'yolov12': 'YOLOv12 是最新官方模型，使用改进的注意力机制，提供更高的检测精度'
}

/**
 * 检测引擎简短描述
 */
export const DETECT_ENGINE_SHORT_DESCRIPTIONS = {
  'yolov8': '基线模型，平衡速度与精度',
  'yolov11-finetuned': '微调模型，专用于单支检测',
  'aps-yolo': '小目标检测优化',
  'deconv-yolo': '可变形卷积增强',
  'rga-crnn': '文字识别专用',
  'yolov12': '最新官方模型，更高精度'
}

/**
 * 检测引擎参数映射表
 * 用于 SAHI (Slicing Aided Hyper Inference) 配置
 */
export const DETECT_ENGINE_PARAMS = {
  'yolov8': {
    slice_size: 640,
    overlap_ratio: 0.25,
    use_soft_nms: true
  },
  'yolov11-finetuned': {
    slice_size: 640,
    overlap_ratio: 0.25,
    use_soft_nms: true
  },
  'aps-yolo': {
    slice_size: 640,
    overlap_ratio: 0.4,
    use_soft_nms: true
  },
  'deconv-yolo': {
    slice_size: 640,
    overlap_ratio: 0.25,
    use_soft_nms: true
  },
  'rga-crnn': {
    slice_size: 512,
    overlap_ratio: 0.35,
    use_soft_nms: true
  },
  'yolov12': {
    slice_size: 640,
    overlap_ratio: 0.25,
    use_soft_nms: true
  }
}

// ==================== 切割引擎参数 ====================

/**
 * 切割引擎默认配置
 */
export const CUT_ENGINE_PARAMS = {
  output_format: 'png',
  add_padding: false,
  padding_size: 10,
  // 支持的输出格式
  supported_formats: ['png', 'jpg', 'jpeg', 'webp']
}

// ==================== 旋转引擎参数 ====================

/**
 * 旋转检测引擎默认配置
 */
export const ROTATION_ENGINE_PARAMS = {
  // 角度检测范围（度）
  min_angle: -45,
  max_angle: 45,
  // 角度步长
  angle_step: 0.5,
  // 是否自动裁剪
  default_auto_crop: true
}

// ==================== 归一化引擎参数 ====================

/**
 * 尺寸归一化引擎默认配置
 */
export const NORMALIZATION_ENGINE_PARAMS = {
  // 默认目标尺寸
  default_target_width: 800,
  default_target_height: 1200,
  // 尺寸范围限制
  min_size: 100,
  max_size: 3000,
  // 尺寸步长
  size_step: 50,
  // 默认保持宽高比
  default_keep_aspect_ratio: true,
  // 默认填充颜色
  default_padding_color: 'white',
  // 支持的填充颜色
  supported_padding_colors: ['white', 'black'],
  // 默认插值方法
  default_interpolation: 'linear',
  // 支持的插值方法
  supported_interpolations: ['nearest', 'linear', 'cubic', 'area', 'lanczos4']
}

// ==================== 工具函数 ====================

/**
 * 获取指定检测引擎的参数
 * @param {string} engineType - 引擎类型
 * @returns {object} SAHI 参数对象
 */
export function getDetectEngineParams(engineType) {
  return DETECT_ENGINE_PARAMS[engineType] || DETECT_ENGINE_PARAMS[DEFAULT_DETECT_ENGINE]
}

/**
 * 获取检测引擎描述
 * @param {string} engineType - 引擎类型
 * @returns {string} 描述信息
 */
export function getDetectEngineDescription(engineType) {
  return DETECT_ENGINE_DESCRIPTIONS[engineType] || DETECT_ENGINE_DESCRIPTIONS[DEFAULT_DETECT_ENGINE]
}

/**
 * 获取检测引擎简短描述
 * @param {string} engineType - 引擎类型
 * @returns {string} 简短描述信息
 */
export function getDetectEngineShortDescription(engineType) {
  return DETECT_ENGINE_SHORT_DESCRIPTIONS[engineType] || DETECT_ENGINE_SHORT_DESCRIPTIONS[DEFAULT_DETECT_ENGINE]
}

/**
 * 获取所有可用的检测引擎
 * @returns {Array} 引擎列表
 */
export function getAvailableDetectEngines() {
  return AVAILABLE_DETECT_ENGINES
}

/**
 * 验证检测引擎是否有效
 * @param {string} engineType - 引擎类型
 * @returns {boolean} 是否有效
 */
export function isValidDetectEngine(engineType) {
  return AVAILABLE_DETECT_ENGINES.some(engine => engine.value === engineType)
}
