/**
 * 简牍 Slip API
 */
import axios from 'axios'
import pinia from '@/store'
import { useUserStore } from '@/store/user'

const API_BASE_URL = import.meta.env.VITE_BACKEND_BASE_URL || 'http://127.0.0.1:8000'

const userStore = useUserStore(pinia)

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
 * Slip API
 */
export const slipsAPI = {
  /**
   * 获取指定组的简牍列表
   * @param {string} groupId - 组ID
   * @param {Object} filters - 筛选参数
   * @returns {Promise<Array>} 简牍列表
   */
  async getSlipsByGroup(groupId, filters = {}) {
    return await apiClient.get(`/api/groups/${groupId}/segments`, {
      params: {
        type: 'slip',
        ...filters
      }
    })
  },

  /**
   * 获取指定简牍下的单字列表
   * @param {string} slipId - 简牍ID
   * @param {string} groupId - 组ID
   * @returns {Promise<Array>} 单字列表
   */
  async getCharsBySlip(slipId, groupId) {
    return await apiClient.get(`/api/groups/${groupId}/segments`, {
      params: {
        type: 'char',
        parent_id: slipId
      }
    })
  },

  /**
   * 获取简牍元数据
   * @param {string} slipId - 简牍ID
   * @returns {Promise<Object>} 简牍详情（含元数据）
   */
  async getSlipMetadata(slipId) {
    return await apiClient.get(`/api/metadata/segments/${slipId}`)
  },

  /**
   * 更新简牍元数据
   * @param {string} slipId - 简牍ID
   * @param {Object} data - 元数据内容
   * @returns {Promise<Object>} 更新结果
   */
  async updateSlipMetadata(slipId, data) {
    return await apiClient.post(`/api/metadata/segments/${slipId}/metadata`, data)
  },

  /**
   * 批量更新简牍元数据
   * @param {string[]} slipIds - 简牍ID数组
   * @param {Object} data - 要更新的元数据
   * @returns {Promise<Object>} 批量更新结果
   */
  async batchUpdateSlipMetadata(slipIds, data) {
    return await apiClient.post('/api/metadata/segments/batch-update', {
      segment_ids: slipIds,
      metadata: data
    })
  },

  /**
   * 删除简牍
   * @param {string} slipId - 简牍ID
   * @returns {Promise<Object>} 删除结果
   */
  async deleteSlip(slipId) {
    return await apiClient.delete(`/api/metadata/segments/${slipId}`)
  }
}

export default slipsAPI
