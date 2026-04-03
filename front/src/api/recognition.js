/**
 * recognition 批量检测 API
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

const recognitionAPI = {
  /**
   * 批量检测单支简牍
   * @param {string} groupId - 图像组ID
   * @returns {Promise<Object>} { task_id, group_id, total_images, status }
   */
  batchDetectSlips(groupId) {
    return apiClient.post('/api/recognition/batch-detect-slips', { group_id: groupId })
  },

  /**
   * 批量检测单字符
   * @param {string} groupId - 图像组ID
   * @returns {Promise<Object>} { task_id, group_id, total_images, status }
   */
  batchDetectChars(groupId) {
    return apiClient.post('/api/recognition/batch-detect-chars', { group_id: groupId })
  }
}

export { recognitionAPI }
