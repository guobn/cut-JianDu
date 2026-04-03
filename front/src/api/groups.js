/**
 * 图像组管理 API
 */
import axios from 'axios'
import pinia from '@/store'
import { useUserStore } from '@/store/user'

const API_BASE_URL = import.meta.env.VITE_BACKEND_BASE_URL || 'http://127.0.0.1:8000'

const userStore = useUserStore(pinia)

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 120秒超时（用于大文件上传）
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
    const errorMessage = error.response?.data?.error_message || error.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new Error(errorMessage))
  }
)

/**
 * 图像组 API
 */
export const groupsAPI = {
  /**
   * 创建图像组
   * @param {Object} data - 组信息
   * @returns {Promise<Object>} 创建的组信息
   */
  async createGroup(data) {
    return await apiClient.post('/api/groups', {
      name: data.name,
      description: data.description,
      source_site: data.source_site,
      period: data.period,
      material: data.material,
      collection: data.collection,
      excavation_year: data.excavation_year,
      batch_no: data.batch_no
    })
  },

  /**
   * 获取所有图像组
   * @returns {Promise<Array>} 图像组列表
   */
  async getGroups() {
    return await apiClient.get('/api/groups')
  },

  /**
   * 获取单个图像组详情
   * @param {string} groupId - 组ID
   * @returns {Promise<Object>} 组详情
   */
  async getGroupDetail(groupId) {
    return await apiClient.get(`/api/groups/${groupId}`)
  },

  /**
   * 更新图像组
   * @param {string} groupId - 组ID
   * @param {Object} data - 更新数据
   * @returns {Promise<Object>} 更新后的组信息
   */
  async updateGroup(groupId, data) {
    return await apiClient.put(`/api/groups/${groupId}`, data)
  },

  /**
   * 删除图像组
   * @param {string} groupId - 组ID
   * @returns {Promise<Object>} 删除结果
   */
  async deleteGroup(groupId) {
    return await apiClient.delete(`/api/groups/${groupId}`)
  },

  /**
   * 上传图片到图像组（multipart）
   * @param {string} groupId - 组ID
   * @param {Array<File>} files - 文件列表
   * @param {Function} onProgress - 进度回调
   * @returns {Promise<Object>} 上传结果
   */
  async uploadImages(groupId, files, onProgress = null) {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })

    const config = {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 300000 // 5分钟超时
    }

    if (onProgress) {
      config.onUploadProgress = (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        onProgress({
          loaded: progressEvent.loaded,
          total: progressEvent.total,
          percent: percentCompleted
        })
      }
    }

    return await apiClient.post(`/api/groups/${groupId}/images`, formData, config)
  },

  /**
   * 获取图像组的图片列表
   * @param {string} groupId - 组ID
   * @param {number} page - 页码（从1开始）
   * @param {number} pageSize - 每页数量
   * @returns {Promise<Object>} 分页的图片列表
   */
  async getGroupImages(groupId, page = 1, pageSize = 20) {
    return await apiClient.get(`/api/groups/${groupId}/images`, {
      params: { page, page_size: pageSize }
    })
  },

  /**
   * 删除图像组中的单张图片
   * @param {string} groupId - 组ID
   * @param {string} imageId - 图片ID
   * @returns {Promise<Object>} 删除结果
   */
  async deleteImage(groupId, imageId) {
    return await apiClient.delete(`/api/groups/${groupId}/images/${imageId}`)
  },

  /**
   * 获取图像组的 segments（检测框）
   * @param {string} groupId - 组ID
   * @param {string} sourceImageId - 源图像ID（可选）
   * @param {string} type - 类型过滤 slip/char（可选）
   * @param {boolean} validated - 验证状态过滤（可选）
   * @returns {Promise<Object>} segments 列表
   */
  async getGroupSegments(groupId, { sourceImageId, type, validated } = {}) {
    const params = {}
    if (sourceImageId) params.source_image_id = sourceImageId
    if (type) params.type = type
    if (validated !== undefined) params.validated = validated
    return await apiClient.get(`/api/groups/${groupId}/segments`, { params })
  },

  /**
   * 更新 segment（检测框）信息
   * @param {string} groupId - 组ID
   * @param {string} segmentId - 片段ID
   * @param {Object} data - 更新数据 { bbox_x, bbox_y, bbox_width, bbox_height }
   * @returns {Promise<Object>} 更新后的 segment
   */
  async updateSegment(groupId, segmentId, data) {
    return await apiClient.put(`/api/groups/${groupId}/segments/${segmentId}`, data)
  },

  /**
   * 删除 segment（检测框）
   * @param {string} groupId - 组ID
   * @param {string} segmentId - 片段ID
   * @returns {Promise<Object>} 删除结果
   */
  async deleteSegment(groupId, segmentId) {
    return await apiClient.delete(`/api/groups/${groupId}/segments/${segmentId}`)
  },

  /**
   * 创建新的 segment（检测框）
   * @param {string} groupId - 组ID
   * @param {Object} data - 片段数据
   * @returns {Promise<Object>} 创建的片段
   */
  async createSegment(groupId, data) {
    return await apiClient.post(`/api/groups/${groupId}/segments`, data)
  },

  /**
   * 获取图像组处理进度
   * @param {string} groupId - 组ID
   * @returns {Promise<Object>} 进度信息
   */
  async getGroupProgress(groupId) {
    return await apiClient.get(`/api/groups/${groupId}/progress`)
  },

  /**
   * 获取图像组验证状态
   * @param {string} groupId - 组ID
   * @returns {Promise<Object>} 验证状态
   */
  async getValidationStatus(groupId) {
    return await apiClient.get(`/api/groups/${groupId}/validation-status`)
  },

  /**
   * 批量预处理图像组
   * @param {string} groupId - 组ID
   * @param {Object} config - 预处理配置
   * @returns {Promise<Object>} 任务信息
   */
  async preprocessGroup(groupId, config) {
    return await apiClient.post(`/api/groups/${groupId}/preprocess`, config)
  },

  /**
   * 批量切割单支
   * @param {string} groupId - 组ID
   * @param {Object} config - 切割配置
   * @returns {Promise<Object>} 任务信息
   */
  async segmentSlips(groupId, config) {
    return await apiClient.post(`/api/groups/${groupId}/segment/slips`, config)
  },

  /**
   * 批量切割单字
   * @param {string} groupId - 组ID
   * @param {Object} config - 切割配置
   * @returns {Promise<Object>} 任务信息
   */
  async segmentChars(groupId, config) {
    return await apiClient.post(`/api/groups/${groupId}/segment/chars`, config)
  },

  /**
   * 获取批次处理进度
   * @param {string} groupId - 组ID
   * @param {string} batchTaskId - 批次任务ID
   * @returns {Promise<Object>} 进度信息
   */
  async getBatchProgress(groupId, batchTaskId) {
    return await apiClient.get(`/api/groups/${groupId}/batch-progress`, {
      params: { batch_task_id: batchTaskId }
    })
  },

  /**
   * 校验图像组中的 segments
   * @param {string} groupId - 组ID
   * @param {Object} data - 校验数据 { image_id }
   * @returns {Promise<Object>} 校验结果
   */
  async validateSegments(groupId, data) {
    return await apiClient.put(`/api/groups/${groupId}/segments/validate`, data)
  },

  /**
   * 导出图像组数据
   * @param {string} groupId - 组ID
   * @param {Object} config - 导出配置 { format, include_images }
   * @returns {Promise<Object>} 导出结果
   */
  async exportGroup(groupId, config) {
    return await apiClient.post(`/api/groups/${groupId}/export`, config)
  }
}

export default groupsAPI
