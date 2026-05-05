import { defineStore } from 'pinia'
import { preprocessAPI } from '@/api/preprocess'

function resolveStep(group, images = []) {
  if (!group) return 0
  if (group.preprocess_status === 'normalized') return 6
  if (group.preprocess_status === 'rotated') return 5
  if (group.preprocess_status === 'angle_detected') return 3
  if ((images?.length || 0) > 0) return 1
  return 0
}

export const usePreprocessStore = defineStore('preprocess', {
  state: () => ({
    groups: [],
    currentGroup: null,
    images: [],
    progress: { stage: '', total: 0, done: 0, percent: 0, task_id: null },
    activeStep: 0,
    polling: false,
    pollTimer: null,
    detectionTaskId: null,
    progressError: '',
    uploadPercent: 0,
    rotationSummary: null,
    normalizeParams: null
  }),

  actions: {
    setCurrentGroup(group) {
      this.currentGroup = group
    },

    setActiveStep(step) {
      this.activeStep = step
    },

    async fetchGroups() {
      const groups = await preprocessAPI.listGroups()
      this.groups = groups
      if (!this.currentGroup && groups.length > 0) {
        this.currentGroup = groups[0]
        await this.fetchGroupImages(groups[0].id)
        this.activeStep = resolveStep(this.currentGroup, this.images)
      }
      return groups
    },

    async hydrateGroup(group) {
      this.currentGroup = group
      await this.fetchGroupImages(group.id)
      this.activeStep = resolveStep(group, this.images)
      if (group.preprocess_status === 'angle_detected') {
        await this.fetchAngles(group.id)
      }
      if (group.preprocess_status === 'draft' && this.images.length > 0) {
        const progress = await this.fetchProgress(group.id)
        if (progress.stage === 'detecting_angles') {
          this.activeStep = 2
          this.startPolling(group.id)
        }
      }
      return group
    },

    async createGroup(name) {
      const group = await preprocessAPI.createGroup(name)
      this.groups = [group, ...this.groups.filter((item) => item.id !== group.id)]
      this.currentGroup = group
      this.images = []
      this.progress = { stage: 'draft', total: 0, done: 0, percent: 0, task_id: null }
      this.progressError = ''
      this.activeStep = 1
      return group
    },

    async fetchGroupImages(groupId) {
      const result = await preprocessAPI.listGroupImages(groupId)
      this.images = (result.items || []).map((item) => ({
        ...item,
        id: item.id || item.image_id
      }))
      if (this.currentGroup?.id === groupId) {
        this.currentGroup.total_images = result.total || this.images.length
      }
      return this.images
    },

    async uploadImages(groupId, files) {
      const result = await preprocessAPI.uploadImages(groupId, files, (event) => {
        const total = event.total || 1
        this.uploadPercent = Math.round((event.loaded * 100) / total)
      })
      this.uploadPercent = 100
      await this.fetchGroupImages(groupId)
      this.activeStep = 1
      return result
    },

    async deleteImage(groupId, imageId) {
      await preprocessAPI.deleteImage(groupId, imageId)
      await this.fetchGroupImages(groupId)
    },

    async detectAngles(groupId) {
      const result = await preprocessAPI.detectAngles(groupId)
      this.detectionTaskId = result.task_id
      this.progressError = ''
      this.progress = { stage: 'detecting_angles', total: this.images.length, done: 0, percent: 0, task_id: result.task_id }
      this.activeStep = 2
      this.startPolling(groupId)
      return result
    },

    async fetchProgress(groupId) {
      const progress = await preprocessAPI.getProgress(groupId)
      this.progress = progress
      if (progress.task_id) {
        this.detectionTaskId = progress.task_id
      }
      return progress
    },

    startPolling(groupId) {
      this.stopPolling()
      this.polling = true
      this.pollTimer = window.setInterval(async () => {
        try {
          const progress = await this.fetchProgress(groupId)
          if (progress.stage === 'angle_detected') {
            this.stopPolling()
            this.progressError = ''
            await this.fetchAngles(groupId)
            this.activeStep = 3
            return
          }
          if (progress.stage === 'failed') {
            this.stopPolling()
            this.progressError = '批量估角任务执行失败，请检查 Celery worker 日志后重试。'
          }
        } catch (error) {
          this.stopPolling()
          this.progressError = error.message || '批量估角进度查询失败'
        }
      }, 1500)
    },

    stopPolling() {
      if (this.pollTimer) {
        window.clearInterval(this.pollTimer)
        this.pollTimer = null
      }
      this.polling = false
    },

    async fetchAngles(groupId) {
      this.images = await preprocessAPI.getAngles(groupId)
      return this.images
    },

    async patchAngle(groupId, imageId, payload) {
      const updated = await preprocessAPI.patchAngle(groupId, imageId, payload)
      this.images = this.images.map((image) => (
        image.image_id === imageId || image.id === imageId
          ? { ...image, ...updated }
          : image
      ))
      return updated
    },

    async applyRotation(groupId) {
      const result = await preprocessAPI.applyRotation(groupId)
      this.rotationSummary = result
      if (this.currentGroup?.id === groupId) {
        this.currentGroup.preprocess_status = 'rotated'
      }
      this.activeStep = 5
      return result
    },

    async normalize(groupId, params) {
      const result = await preprocessAPI.normalize(groupId, params)
      this.normalizeParams = params
      if (this.currentGroup?.id === groupId) {
        this.currentGroup.preprocess_status = 'normalized'
      }
      this.activeStep = 6
      return result
    },

    async convert(groupId) {
      const result = await preprocessAPI.convert(groupId)
      this.groups = this.groups.filter((group) => group.id !== groupId)
      if (this.currentGroup?.id === groupId) {
        this.currentGroup = null
        this.images = []
      }
      return result
    }
  }
})
