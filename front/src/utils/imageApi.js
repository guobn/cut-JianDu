import axios from 'axios'

// 创建 axios 实例
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000
})

// 图像处理 API
export const imageAPI = {
  /**
   * 上传图像
   * @param {File} file - 图像文件
   * @returns {Promise} 返回图像信息
   */
  upload: async (file) => {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await api.post('/api/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return data
  },

  /**
   * 检测简牍或字符
   * @param {string} imageId - 图像ID
   * @param {string} mode - 检测模式: "slip" 或 "character"
   * @param {object} params - 检测参数
   * @returns {Promise} 返回检测结果
   */
  detect: async (imageId, mode, params = {}) => {
    const { data } = await api.post('/api/detect', {
      image_id: imageId,
      mode: mode,
      min_width: params.minWidth || (mode === 'slip' ? 50 : 20),
      min_height: params.minHeight || (mode === 'slip' ? 200 : 20)
    })
    return data
  },

  /**
   * 执行切割
   * @param {string} imageId - 图像ID
   * @param {Array} bboxes - 边界框数组 [{x, y, width, height}, ...]
   * @returns {Promise} 返回切割结果
   */
  cut: async (imageId, bboxes) => {
    const { data } = await api.post('/api/cut', {
      image_id: imageId,
      bboxes: bboxes
    })
    return data
  },

  /**
   * 旋转校正
   * @param {string} imageId - 图像ID
   * @param {number|null} angle - 旋转角度，null 为自动检测
   * @returns {Promise} 返回校正结果
   */
  rotate: async (imageId, angle = null) => {
    const { data } = await api.post('/api/rotate', {
      image_id: imageId,
      angle: angle
    })
    return data
  },

  /**
   * 尺寸归一化
   * @param {string} imageId - 图像ID
   * @param {number} targetWidth - 目标宽度
   * @returns {Promise} 返回归一化结果
   */
  normalize: async (imageId, targetWidth = 800) => {
    const { data } = await api.post('/api/normalize', {
      image_id: imageId,
      target_width: targetWidth
    })
    return data
  }
}

// 错误处理拦截器
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // 服务器返回错误
      const message = error.response.data?.detail || error.response.data?.message || '请求失败'
      console.error('API Error:', message)
      return Promise.reject(new Error(message))
    } else if (error.request) {
      // 请求发送但没有响应
      console.error('Network Error:', error.message)
      return Promise.reject(new Error('网络错误，请检查后端服务是否启动'))
    } else {
      // 其他错误
      console.error('Error:', error.message)
      return Promise.reject(error)
    }
  }
)

export default api
