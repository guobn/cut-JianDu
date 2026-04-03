/**
 * 元数据管理 API
 */
import axios from 'axios'
import pinia from '@/store'
import { useUserStore } from '@/store/user'

const API_BASE_URL = import.meta.env.VITE_BACKEND_BASE_URL || 'http://127.0.0.1:8000'

const userStore = useUserStore(pinia)

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json'
  }
})

apiClient.interceptors.request.use((config) => {
  const token = userStore.session?.access_token
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

const metadataAPI = {
  /**
   * 保存片段元数据
   * @param {string} segmentId - 片段ID
   * @param {Object} data - 元数据 { title, content_description, event_type, event_date, place, people, extra }
   * @returns {Promise<Object>} 保存结果
   */
  saveSegmentMetadata(segmentId, data) {
    return apiClient.post(`/api/metadata/segments/${segmentId}/metadata`, data)
  },

  /**
   * 获取片段元数据
   * @param {string} segmentId - 片段ID
   * @returns {Promise<Object>} 元数据
   */
  getSegmentMetadata(segmentId) {
    return apiClient.get(`/api/metadata/segments/${segmentId}`)
  }
}

export { metadataAPI }
