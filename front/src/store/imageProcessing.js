import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import imageProcessingAPI from '@/api/imageProcessing'
import {
  AVAILABLE_DETECT_ENGINES,
  SLIP_DETECT_ENGINES,
  CHARACTER_DETECT_ENGINES,
  DEFAULT_DETECT_ENGINE,
  DETECT_ENGINE_PARAMS,
  DETECT_ENGINE_DESCRIPTIONS,
  DETECT_ENGINE_SHORT_DESCRIPTIONS,
  getDetectEngineParams
} from '@/config/engineParams'

export const useImageProcessingStore = defineStore('imageProcessing', () => {
  // 状态
  const currentImage = ref(null) // 当前图像信息
  const imageUrl = ref(null) // 图像URL
  const detectionResults = ref(null) // 检测结果
  const segmentationResults = ref(null) // 切割结果
  const rotationResults = ref(null) // 旋转结果
  const normalizationResults = ref(null) // 归一化结果
  
  const isUploading = ref(false) // 上传中
  const isDetecting = ref(false) // 检测中
  const isProcessing = ref(false) // 处理中
  
  const error = ref(null) // 错误信息
  
  // 检测引擎选择
  const activeEngine = ref(DEFAULT_DETECT_ENGINE) // 当前活跃的检测引擎
  const availableEngines = ref(AVAILABLE_DETECT_ENGINES)

  // 计算属性
  const hasImage = computed(() => !!currentImage.value)
  const hasDetections = computed(() => detectionResults.value?.detections?.length > 0)
  const detectionCount = computed(() => detectionResults.value?.total_count || 0)
  
  // 引擎参数计算属性
  const engineParams = computed(() => (engineType) => {
    return getDetectEngineParams(engineType)
  })
  
  const getCurrentEngineParams = computed(() => {
    return engineParams.value(activeEngine.value)
  })

  // Actions

  /**
   * 上传图像
   */
  async function uploadImage(file, slipNumber = '') {
    try {
      isUploading.value = true
      error.value = null

      const result = await imageProcessingAPI.uploadImage(file, slipNumber)

      currentImage.value = result
      imageUrl.value = imageProcessingAPI.getImageUrl(result.image_id)

      // 清空之前的结果
      detectionResults.value = null
      segmentationResults.value = null
      rotationResults.value = null
      normalizationResults.value = null

      return result
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isUploading.value = false
    }
  }

  /**
   * 检测单支简牍：先拉取当前图像，再以 multipart 上传给后端检测。
   * 不传 parameters，与后端 detect-upload 默认参数一致，避免前端参数把框滤掉。
   */
  async function detectSlips(parameters = null) {
    if (!currentImage.value) throw new Error('请先上传图像')
    try {
      isDetecting.value = true
      error.value = null
      const result = await imageProcessingAPI.detectRegions(
        currentImage.value.image_id,
        'single-slip',
        null
      )
      const payload = result?.data !== undefined ? result.data : result
      detectionResults.value = payload
      return payload
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isDetecting.value = false
    }
  }

  /**
   * 快速检测单支（同步）
   */
  async function detectSlipsFast(parameters = null) {
    if (!currentImage.value) throw new Error('请先上传图像')
    try {
      isDetecting.value = true
      error.value = null
      const result = await imageProcessingAPI.detectRegionsFast(
        currentImage.value.image_id,
        'single-slip',
        parameters
      )
      const payload = result?.data !== undefined ? result.data : result
      detectionResults.value = payload
      return payload
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isDetecting.value = false
    }
  }

  /**
   * 检测单个文字：先拉取当前图像，再以 multipart 上传给后端检测
   */
  async function detectCharacters(parameters = null) {
    if (!currentImage.value) throw new Error('请先上传图像')
    try {
      isDetecting.value = true
      error.value = null
      const result = await imageProcessingAPI.detectRegions(
        currentImage.value.image_id,
        'single-character',
        parameters
      )
      const payload = result?.data !== undefined ? result.data : result
      detectionResults.value = payload
      return payload
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isDetecting.value = false
    }
  }

  /**
   * 快速检测单字（同步）
   */
  async function detectCharactersFast(parameters = null) {
    if (!currentImage.value) throw new Error('请先上传图像')
    try {
      isDetecting.value = true
      error.value = null
      const result = await imageProcessingAPI.detectRegionsFast(
        currentImage.value.image_id,
        'single-character',
        parameters
      )
      const payload = result?.data !== undefined ? result.data : result
      detectionResults.value = payload
      return payload
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isDetecting.value = false
    }
  }

  /**
   * 执行切割
   */
  async function cutImage(boundingBoxes, options = {}) {
    if (!currentImage.value) {
      throw new Error('请先上传图像')
    }

    if (!boundingBoxes || boundingBoxes.length === 0) {
      throw new Error('请先检测或添加边界框')
    }

    try {
      isProcessing.value = true
      error.value = null

      const result = await imageProcessingAPI.cutImage(
        currentImage.value.image_id,
        boundingBoxes,
        options
      )

      segmentationResults.value = result
      return result
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isProcessing.value = false
    }
  }

  /**
   * 检测旋转角度
   */
  async function detectRotationAngle() {
    if (!currentImage.value) {
      throw new Error('请先上传图像')
    }

    try {
      isDetecting.value = true
      error.value = null

      const result = await imageProcessingAPI.detectRotationAngle(
        currentImage.value.image_id
      )

      return result
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isDetecting.value = false
    }
  }

  /**
   * 快速检测旋转角度（同步）
   */
  async function detectRotationAngleFast() {
    if (!currentImage.value) {
      throw new Error('请先上传图像')
    }

    try {
      isDetecting.value = true
      error.value = null

      const result = await imageProcessingAPI.detectRotationAngleFast(
        currentImage.value.image_id
      )

      return result
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isDetecting.value = false
    }
  }

  /**
   * 执行旋转校正
   */
  async function correctRotation(angle = null, autoCrop = true) {
    if (!currentImage.value) {
      throw new Error('请先上传图像')
    }

    try {
      isProcessing.value = true
      error.value = null

      const result = await imageProcessingAPI.correctRotation(
        currentImage.value.image_id,
        angle,
        autoCrop
      )

      rotationResults.value = result
      return result
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isProcessing.value = false
    }
  }

  /**
   * 快速执行旋转校正（同步）
   */
  async function correctRotationFast(angle = null, autoCrop = true) {
    if (!currentImage.value) {
      throw new Error('请先上传图像')
    }

    try {
      isProcessing.value = true
      error.value = null

      const result = await imageProcessingAPI.correctRotationFast(
        currentImage.value.image_id,
        angle,
        autoCrop
      )

      rotationResults.value = result
      return result
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isProcessing.value = false
    }
  }

  /**
   * 执行尺寸归一化
   */
  async function normalizeSize(options = {}) {
    if (!currentImage.value) {
      throw new Error('请先上传图像')
    }

    try {
      isProcessing.value = true
      error.value = null

      const result = await imageProcessingAPI.normalizeSize(
        currentImage.value.image_id,
        options
      )

      normalizationResults.value = result
      return result
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isProcessing.value = false
    }
  }

  /**
   * 更新检测结果（用于手动编辑边界框后）
   */
  function updateDetectionResults(detections) {
    if (detectionResults.value) {
      detectionResults.value.detections = detections
      detectionResults.value.total_count = detections.length
    }
  }

  /**
   * 清空当前图像和结果
   */
  function clearAll() {
    currentImage.value = null
    imageUrl.value = null
    detectionResults.value = null
    segmentationResults.value = null
    rotationResults.value = null
    normalizationResults.value = null
    error.value = null
  }

  /**
   * 清空错误
   */
  function clearError() {
    error.value = null
  }

  /**
   * 设置当前使用的检测引擎
   * @param {string} engine - 引擎类型：'yolov8', 'yolov11-finetuned', 'aps-yolo', 'deconv-yolo', 'rga-crnn', 'yolov12'
   * @param {string} mode - 模式：'slip' 或 'character'，用于验证引擎有效性
   */
  function setActiveEngine(engine, mode = 'slip') {
    const validEngines = mode === 'slip'
      ? SLIP_DETECT_ENGINES.map(e => e.value)
      : CHARACTER_DETECT_ENGINES.map(e => e.value)
    if (!validEngines.includes(engine)) {
      throw new Error(`Invalid detection engine: ${engine}. Valid options for ${mode} mode: ${validEngines.join(', ')}`)
    }
    activeEngine.value = engine
  }

  /**
   * 获取指定引擎的 SAHI 参数
   * @param {string} engineType - 引擎类型
   * @returns {object} SAHI 参数对象
   */
  function getEngineParams(engineType) {
    return getDetectEngineParams(engineType)
  }

  return {
    // 状态
    currentImage,
    imageUrl,
    detectionResults,
    segmentationResults,
    rotationResults,
    normalizationResults,
    isUploading,
    isDetecting,
    isProcessing,
    error,

    // 计算属性
    hasImage,
    hasDetections,
    detectionCount,

    // Actions
    uploadImage,
    detectSlips,
    detectSlipsFast,
    detectCharacters,
    detectCharactersFast,
    cutImage,
    detectRotationAngle,
    detectRotationAngleFast,
    correctRotation,
    correctRotationFast,
    normalizeSize,
    updateDetectionResults,
    clearAll,
    clearError,
    setActiveEngine,
    getEngineParams,
    engineParams,
    getCurrentEngineParams,
    activeEngine,
    availableEngines
  }
})
