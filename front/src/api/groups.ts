/**
 * 图像组相关 API 调用
 */
import axios from 'axios'
import type {
  ImageGroup,
  ImageGroupCreate,
  ImageGroupUpdate,
  ProcessingCache,
  ExportRecord,
  ExportStatus,
  ProcessProgress
} from '@/types/groups'

const API_BASE = '/api'

// 图像组 API
export const groupsAPI = {
  // 创建图像组
  createGroup(data: ImageGroupCreate) {
    return axios.post<ImageGroup>(`${API_BASE}/groups`, data)
  },

  // 获取所有图像组
  getGroups() {
    return axios.get<ImageGroup[]>(`${API_BASE}/groups`)
  },

  // 获取单个图像组
  getGroup(id: string) {
    return axios.get<ImageGroup>(`${API_BASE}/groups/${id}`)
  },

  // 更新图像组
  updateGroup(id: string, data: ImageGroupUpdate) {
    return axios.put<ImageGroup>(`${API_BASE}/groups/${id}`, data)
  },

  // 删除图像组
  deleteGroup(id: string) {
    return axios.delete(`${API_BASE}/groups/${id}`)
  },

  // 批量预处理
  preprocessGroup(id: string, config: any) {
    return axios.post(`${API_BASE}/groups/${id}/preprocess`, config)
  },

  // 批量切割单支
  segmentSlips(id: string, config: any) {
    return axios.post(`${API_BASE}/groups/${id}/segment/slips`, config)
  },

  // 批量切割单字
  segmentChars(id: string, config: any) {
    return axios.post(`${API_BASE}/groups/${id}/segment/chars`, config)
  },

  // 获取处理进度
  getProgress(id: string) {
    return axios.get<ProcessProgress>(`${API_BASE}/groups/${id}/progress`)
  },

  // 批量更新元数据
  batchUpdateMetadata(id: string, data: any) {
    return axios.put(`${API_BASE}/groups/${id}/batch-metadata`, data)
  },

  // 导出数据
  exportGroup(id: string, config: any) {
    return axios.post<ExportRecord>(`${API_BASE}/groups/${id}/export`, config)
  }
}

// 缓存 API
export const cacheAPI = {
  // 保存缓存
  saveCache(data: any) {
    return axios.post(`${API_BASE}/cache/save`, data)
  },

  // 获取缓存
  getCache(sourceImageId: string, cacheType: string) {
    return axios.get<ProcessingCache>(`${API_BASE}/cache/${sourceImageId}/${cacheType}`)
  },

  // 删除缓存
  deleteCache(sourceImageId: string) {
    return axios.delete(`${API_BASE}/cache/${sourceImageId}`)
  }
}

// 导出 API
export const exportsAPI = {
  // 获取导出状态
  getExportStatus(exportId: string) {
    return axios.get<ExportStatus>(`${API_BASE}/exports/${exportId}/status`)
  }
}

export default {
  groupsAPI,
  cacheAPI,
  exportsAPI
}
