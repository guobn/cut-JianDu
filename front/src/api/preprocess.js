import request from '@/utils/request'

export const preprocessAPI = {
  async createGroup(name) {
    const response = await request.post('/api/preprocess/groups', { name })
    return response.data
  },

  async listGroups() {
    const response = await request.get('/api/preprocess/groups')
    return response.data
  },

  async uploadImages(groupId, files, onUploadProgress) {
    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    const response = await request.post(`/api/preprocess/groups/${groupId}/upload`, formData, {
      timeout: 300000,
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress
    })
    return response.data
  },

  async detectAngles(groupId) {
    const response = await request.post(`/api/preprocess/groups/${groupId}/detect-angles`)
    return response.data
  },

  async getProgress(groupId) {
    const response = await request.get(`/api/preprocess/groups/${groupId}/progress`)
    return response.data
  },

  async getAngles(groupId) {
    const response = await request.get(`/api/preprocess/groups/${groupId}/angles`)
    return response.data
  },

  async patchAngle(groupId, imageId, payload) {
    const response = await request.patch(`/api/preprocess/groups/${groupId}/angles/${imageId}`, payload)
    return response.data
  },

  async applyRotation(groupId) {
    const response = await request.post(`/api/preprocess/groups/${groupId}/apply-rotation`)
    return response.data
  },

  async normalize(groupId, payload) {
    const response = await request.post(`/api/preprocess/groups/${groupId}/normalize`, payload)
    return response.data
  },

  async convert(groupId) {
    const response = await request.post(`/api/preprocess/groups/${groupId}/convert`)
    return response.data
  },

  async deleteGroup(groupId) {
    const response = await request.delete(`/api/preprocess/groups/${groupId}`)
    return response.data
  },

  async listGroupImages(groupId) {
    const response = await request.get(`/api/groups/${groupId}/images`, {
      params: { page: 1, page_size: 200 }
    })
    return response.data
  },

  async deleteImage(groupId, imageId) {
    const response = await request.delete(`/api/groups/${groupId}/images/${imageId}`)
    return response.data
  }
}

export default preprocessAPI
