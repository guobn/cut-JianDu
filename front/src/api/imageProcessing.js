import axios from 'axios'
import pinia from '@/store'
import { useUserStore } from '@/store/user'
import { NORMALIZATION_ENGINE_PARAMS } from '@/config/engineParams'

const API_BASE_URL = import.meta.env.VITE_BACKEND_BASE_URL || 'http://127.0.0.1:8000'

const userStore = useUserStore(pinia)

// 超时配置表：根据任务类型设置不同的超时时间（毫秒）
const TIMEOUT_CONFIG = {
  detect: 60000,        // 检测区域：60 秒
  cut: 120000,          // 切割：120 秒
  rotation: 90000,      // 旋转检测：90 秒
  normalization: 60000, // 尺寸归一化：60 秒
  batch: 300000,        // 批量处理：300 秒
  export: 600000        // 导出：600 秒
}

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60秒超时
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    const token = userStore.session?.access_token
    if (token) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${token}`
    }
    // 发送 FormData 时不要带 Content-Type，让浏览器设为 multipart/form-data; boundary=...
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const errorMessage = error.response?.data?.error_message || error.message || '请求失败'
    return Promise.reject(new Error(errorMessage))
  }
)

/**
 * 图像处理 API
 */
export const imageProcessingAPI = {
  /**
   * 上传图像
   * @param {File} file - 图像文件
   * @param {string} slipNumber - 简牍编号(可选)
   * @returns {Promise<Object>} 图像信息
   */
  async uploadImage(file, slipNumber = '') {
    const formData = new FormData()
    formData.append('file', file)
    if (slipNumber) {
      formData.append('slip_number', slipNumber)
    }

    const token = userStore.session?.access_token
    const response = await axios.post(`${API_BASE_URL}/api/images/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      timeout: 60000
    })

    return response.data
  },

  /**
   * 获取图像列表
   * @param {number} limit - 返回的最大数量
   * @returns {Promise<Array>} 图像列表
   */
  async listImages(limit = 50) {
    return await apiClient.get('/api/images/', {
      params: { limit }
    })
  },

  /**
   * 获取图像
   * @param {string} imageId - 图像ID
   * @returns {Promise<string>} 图像URL
   */
  getImageUrl(imageId) {
    // 添加时间戳避免缓存问题
    const timestamp = new Date().getTime()
    return `${API_BASE_URL}/api/images/${imageId}?t=${timestamp}`
  },

  /**
   * 拉取图像为 Blob。先试 fetch，失败（如 CORS / Failed to fetch）时用 axios 回退。
   * @param {string} imageId - 图像ID
   * @returns {Promise<Blob>} 图像 Blob
   */
  async getImageBlob(imageId) {
    const url = this.getImageUrl(imageId)
    const token = userStore.session?.access_token
    try {
      const res = await fetch(url, {
        credentials: 'include',
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      })
      if (!res.ok) throw new Error(`获取图像失败: ${res.status}`)
      const blob = await res.blob()
      console.info('[getImageBlob] fetch ok, imageId=%s, blob.size=%s', imageId, blob.size)
      return blob
    } catch (e) {
      try {
        const blob = await apiClient.get(`/api/images/${imageId}`, { responseType: 'blob' })
        console.info('[getImageBlob] axios 回退 ok, imageId=%s, blob.size=%s', imageId, blob?.size)
        return blob
      } catch (axErr) {
        throw new Error(e?.message || axErr?.message || '获取图像失败')
      }
    }
  },

  /**
   * 检测区域：先拉取当前图像，再以 multipart 上传给后端
   * @param {string} imageId - 图像ID
   * @param {string} mode - 'single-slip' | 'single-character'
   * @param {Object} parameters - 检测参数（null 则后端用默认，单支建议传 null 与 detect-upload 一致）
   * @returns {Promise<Object>} 检测结果
   */
  async getTaskStatus(taskId) {
    return await apiClient.get(`/api/tasks/${taskId}`)
  },

  async pollTask(taskId, taskType = 'detect', interval = 1000) {
    // 根据任务类型获取超时时间，支持直接传入数字作为超时时间
    const timeout = typeof taskType === 'number' ? taskType : (TIMEOUT_CONFIG[taskType] || TIMEOUT_CONFIG.detect)
    const startTime = Date.now()

    while (true) {
      const status = await this.getTaskStatus(taskId)
      console.info('[pollTask] taskId=%s, status=%s, result=%o', taskId, status.status, status.result)

      // 后端返回小写状态：'success', 'failure', 'pending', 'started'
      if (status.status === 'success') {
        return status.result
      }

      if (status.status === 'failure') {
        throw new Error(status.error || '任务执行失败')
      }

      if (Date.now() - startTime > timeout) {
        throw new Error('任务超时')
      }

      await new Promise(resolve => setTimeout(resolve, interval))
    }
  },

  async detectRegions(imageId, mode, parameters = null) {
    const blob = await this.getImageBlob(imageId)
    const form = new FormData()
    const ext = (blob.type || '').includes('png') ? 'png' : 'jpg'
    form.append('file', new File([blob], `image.${ext}`, { type: blob.type || 'image/jpeg' }))
    form.append('image_id', imageId)
    form.append('mode', mode)
    if (parameters != null && Object.keys(parameters).length > 0) {
      form.append('parameters', JSON.stringify(parameters))
    }
    console.info('[detectRegions] 发送：imageId=%s, mode=%s, parameters=%o, 文件大小=%s', imageId, mode, parameters, blob.size)

    const submitResponse = await apiClient.post('/api/segmentation/detect', form)
    console.info('[detectRegions] 任务已提交：taskId=%s', submitResponse.task_id)

    const result = await this.pollTask(submitResponse.task_id, 'detect')
    console.info('[detectRegions] 任务完成：taskId=%s, result=%o', submitResponse.task_id, result)

    return result
  },

  /**
   * 快速检测区域（同步）：直接返回结果，不使用 Celery 异步任务
   * @param {string} imageId - 图像ID
   * @param {string} mode - 'single-slip' | 'single-character'
   * @param {Object} parameters - 检测参数
   * @returns {Promise<Object>} 检测结果
   */
  async detectRegionsFast(imageId, mode, parameters = null) {
    const blob = await this.getImageBlob(imageId)
    const form = new FormData()
    const ext = (blob.type || '').includes('png') ? 'png' : 'jpg'
    form.append('file', new File([blob], `image.${ext}`, { type: blob.type || 'image/jpeg' }))
    form.append('image_id', imageId)
    form.append('mode', mode)
    if (parameters != null && Object.keys(parameters).length > 0) {
      form.append('parameters', JSON.stringify(parameters))
    }
    console.info('[detectRegionsFast] 发送：imageId=%s, mode=%s, parameters=%o, 文件大小=%s', imageId, mode, parameters, blob.size)

    const result = await apiClient.post('/api/segmentation/detect-fast', form)
    console.info('[detectRegionsFast] 完成：result=%o', result)

    // 转换为与异步版本相同的格式
    return {
      detections: result.bounding_boxes || [],
      total_count: result.total_count || 0,
      processing_time: result.processing_time
    }
  },

  /**
   * 执行切割
   * @param {string} imageId - 图像ID
   * @param {Array} boundingBoxes - 边界框列表
   * @param {Object} options - 切割选项
   * @returns {Promise<Object>} 切割结果
   */
  async cutImage(imageId, boundingBoxes, options = {}) {
    return await apiClient.post('/api/segmentation/cut', {
      image_id: imageId,
      bounding_boxes: boundingBoxes,
      output_format: options.outputFormat || 'png',
      add_padding: options.addPadding || false,
      padding_size: options.paddingSize || 10,
      // 当从“单支图片”进行单字切割时，前端会传入 parentSegmentId，
      // 后端据此在 Supabase 中建立原图 -> 单支 -> 单字的层级关系。
      parent_segment_id: options.parentSegmentId || null
    })
  },

  /**
   * 检测旋转角度
   * @param {string} imageId - 图像ID
   * @returns {Promise<Object>} 角度检测结果
   */
  async detectRotationAngle(imageId) {
    return await apiClient.post(`/api/rotation/detect-angle?image_id=${imageId}`)
  },

  /**
   * 快速检测旋转角度（同步）
   * @param {string} imageId - 图像ID
   * @returns {Promise<Object>} 角度检测结果
   */
  async detectRotationAngleFast(imageId) {
    const submitResponse = await apiClient.post(`/api/rotation/detect-angle-fast?image_id=${imageId}`)
    console.info('[detectRotationAngleFast] 完成：result=%o', submitResponse)
    return submitResponse
  },

  /**
   * 执行旋转校正
   * @param {string} imageId - 图像ID
   * @param {number|null} angle - 指定角度（null 则自动检测）
   * @param {boolean} autoCrop - 是否自动裁剪
   * @returns {Promise<Object>} 校正结果
   */
  async correctRotation(imageId, angle = null, autoCrop = true) {
    return await apiClient.post('/api/rotation/correct', {
      image_id: imageId,
      angle: angle,
      auto_crop: autoCrop
    })
  },

  /**
   * 快速执行旋转校正（同步）
   * @param {string} imageId - 图像ID
   * @param {number|null} angle - 指定角度（null 则自动检测）
   * @param {boolean} autoCrop - 是否自动裁剪
   * @returns {Promise<Object>} 校正结果
   */
  async correctRotationFast(imageId, angle = null, autoCrop = true) {
    const submitResponse = await apiClient.post('/api/rotation/correct-fast', {
      image_id: imageId,
      angle: angle,
      auto_crop: autoCrop
    })
    console.info('[correctRotationFast] 完成：result=%o', submitResponse)
    return submitResponse
  },

  /**
   * 执行尺寸归一化
   * @param {string} imageId - 图像ID
   * @param {Object} options - 归一化选项
   * @returns {Promise<Object>} 归一化结果
   */
  async normalizeSize(imageId, options = {}) {
    return await apiClient.post('/api/normalization/normalize', {
      image_id: imageId,
      target_width: options.targetWidth || NORMALIZATION_ENGINE_PARAMS.default_target_width,
      target_height: options.targetHeight || NORMALIZATION_ENGINE_PARAMS.default_target_height,
      keep_aspect_ratio: options.keepAspectRatio !== false,
      padding_color: options.paddingColor || NORMALIZATION_ENGINE_PARAMS.default_padding_color,
      interpolation: options.interpolation || NORMALIZATION_ENGINE_PARAMS.default_interpolation
    })
  },

  /**
   * 健康检查
   * @returns {Promise<Object>} 健康状态
   */
  async healthCheck() {
    return await apiClient.get('/health')
  },

  /**
   * 获取切割结果列表（带元数据）
   * @param {Object} params - 查询参数
   * @returns {Promise<Array>} 切割结果列表
   */
  async listSegments(params = {}) {
    return await apiClient.get('/api/metadata/segments', { params })
  },

  /**
   * 便捷方法：按原图 ID 查询所有单支
   */
  async listSlipSegmentsByImage(imageId, limit = 200) {
    return await this.listSegments({
      image_id: imageId,
      segment_type: 'slip',
      limit
    })
  },

  /**
   * 便捷方法：按父级单支 segment 查询所有单字
   */
  async listCharSegmentsByParent(parentSegmentId, limit = 500) {
    return await this.listSegments({
      parent_segment_id: parentSegmentId,
      segment_type: 'char',
      limit
    })
  },

  /**
   * 获取单个切割结果及其元数据
   * @param {string} segmentId - 切割结果ID
   * @returns {Promise<Object>} 切割结果详情
   */
  async getSegment(segmentId) {
    return await apiClient.get(`/api/metadata/segments/${segmentId}`)
  },

  /**
   * 创建或更新切割结果的元数据
   * @param {string} segmentId - 切割结果ID
   * @param {Object} metadata - 元数据内容
   * @returns {Promise<Object>} 操作结果
   */
  async upsertSegmentMetadata(segmentId, metadata) {
    return await apiClient.post(`/api/metadata/segments/${segmentId}/metadata`, metadata)
  },

  /**
   * 删除单个切割结果
   * @param {string} segmentId - 切割结果ID
   * @returns {Promise<Object>} 操作结果
   */
  async deleteSegment(segmentId) {
    return await apiClient.delete(`/api/metadata/segments/${segmentId}`)
  },

  /**
   * 批量删除切割结果
   * @param {string[]} segmentIds - 切割结果ID数组
   * @returns {Promise<Object>} 操作结果
   */
  async deleteSegments(segmentIds) {
    return await apiClient.post('/api/metadata/segments/batch-delete', segmentIds)
  }
}

export default imageProcessingAPI
