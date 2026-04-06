/**
 * 图像组状态管理 Store
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { groupsAPI } from '@/api/groups'

export const useGroupStore = defineStore('group', () => {
  // 状态
  const groups = ref([])
  const currentGroup = ref(null)
  const currentGroupImages = ref([])
  const currentGroupImagesTotal = ref(0)
  const currentGroupImagesPage = ref(1)
  const currentGroupImagesPageSize = ref(20)
  const isLoading = ref(false)
  const imagesLoading = ref(false)
  const progressMap = ref({})
  const validationStatusMap = ref({})

  // 计算属性
  const activeGroup = computed(() => {
    return currentGroup.value
  })

  const totalPages = computed(() => {
    if (currentGroupImagesTotal.value === 0) return 1
    return Math.ceil(currentGroupImagesTotal.value / currentGroupImagesPageSize.value)
  })

  // 方法
  const setGroups = (newGroups) => {
    groups.value = newGroups
  }

  const setCurrentGroup = (group) => {
    currentGroup.value = group
  }

  const setCurrentGroupImages = (images, total = 0) => {
    currentGroupImages.value = images
    currentGroupImagesTotal.value = total
  }

  const setCurrentGroupImagesPage = (page) => {
    currentGroupImagesPage.value = page
  }

  const setIsLoading = (loading) => {
    isLoading.value = loading
  }

  const setImagesLoading = (loading) => {
    imagesLoading.value = loading
  }

  const updateProgress = (groupId, progress) => {
    progressMap.value[groupId] = progress
  }

  const clearProgress = (groupId) => {
    delete progressMap.value[groupId]
  }

  const updateValidationStatus = (groupId, status) => {
    validationStatusMap.value[groupId] = status
  }

  const addGroup = (group) => {
    groups.value.push(group)
  }

  const removeGroup = (groupId) => {
    groups.value = groups.value.filter(g => g.id !== groupId)
  }

  const updateGroup = (groupId, updates) => {
    const index = groups.value.findIndex(g => g.id === groupId)
    if (index !== -1) {
      groups.value[index] = { ...groups.value[index], ...updates }
    }
    if (currentGroup.value?.id === groupId) {
      currentGroup.value = { ...currentGroup.value, ...updates }
    }
  }

  const addImagesToGroup = (groupId, newImages) => {
    const group = groups.value.find(g => g.id === groupId)
    if (group) {
      group.total_images = (group.total_images || 0) + newImages.length
      // 更新缩略图为第一张新图片（如果组没有缩略图）
      if (!group.thumbnail_url && newImages.length > 0) {
        group.thumbnail_url = newImages[0].thumbnail_url
      }
    }
  }

  const removeImageFromGroup = (groupId) => {
    const group = groups.value.find(g => g.id === groupId)
    if (group && group.total_images > 0) {
      group.total_images -= 1
    }
    currentGroupImages.value = currentGroupImages.value.filter(img => img.id !== imageId)
  }

  // Action: 获取所有图像组
  const fetchGroups = async () => {
    isLoading.value = true
    try {
      const data = await groupsAPI.getGroups()
      groups.value = data || []
      return groups.value
    } catch (error) {
      console.error('获取图像组列表失败:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  // Action: 创建图像组
  const createGroup = async (groupData) => {
    isLoading.value = true
    try {
      const newGroup = await groupsAPI.createGroup(groupData)
      groups.value.unshift(newGroup)
      return newGroup
    } catch (error) {
      console.error('创建图像组失败:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  // Action: 获取图像组详情
  const fetchGroupDetail = async (groupId) => {
    isLoading.value = true
    try {
      const data = await groupsAPI.getGroupDetail(groupId)
      currentGroup.value = data
      // 更新 groups 列表中的对应组
      const index = groups.value.findIndex(g => g.id === groupId)
      if (index !== -1) {
        groups.value[index] = data
      }
      return data
    } catch (error) {
      console.error('获取图像组详情失败:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  // Action: 上传图片
  const uploadImages = async (groupId, files, onProgress = null) => {
    imagesLoading.value = true
    try {
      const result = await groupsAPI.uploadImages(groupId, files, onProgress)
      // 更新组信息
      const group = groups.value.find(g => g.id === groupId)
      if (group) {
        group.total_images = (group.total_images || 0) + result.total_uploaded
        // 如果组没有缩略图，使用第一张上传图片的缩略图
        if (!group.thumbnail_url && result.uploaded && result.uploaded.length > 0) {
          group.thumbnail_url = result.uploaded[0].thumbnail_url
        }
      }
      return result
    } catch (error) {
      console.error('上传图片失败:', error)
      throw error
    } finally {
      imagesLoading.value = false
    }
  }

  // Action: 获取图像组图片列表
  const fetchImages = async (groupId, page = 1, pageSize = 20) => {
    imagesLoading.value = true
    currentGroupImagesPage.value = page
    try {
      const result = await groupsAPI.getGroupImages(groupId, page, pageSize)
      currentGroupImages.value = result.items || []
      currentGroupImagesTotal.value = result.total || 0
      currentGroupImagesPageSize.value = pageSize
      return result
    } catch (error) {
      console.error('获取图片列表失败:', error)
      throw error
    } finally {
      imagesLoading.value = false
    }
  }

  // Action: 删除图片
  const deleteImage = async (groupId, imageId) => {
    try {
      await groupsAPI.deleteImage(groupId, imageId)
      // 从当前列表移除
      currentGroupImages.value = currentGroupImages.value.filter(img => img.id !== imageId)
      currentGroupImagesTotal.value = Math.max(0, currentGroupImagesTotal.value - 1)
      // 更新组信息
      const group = groups.value.find(g => g.id === groupId)
      if (group && group.total_images > 0) {
        group.total_images -= 1
      }
    } catch (error) {
      console.error('删除图片失败:', error)
      throw error
    }
  }

  // Action: 删除图像组
  const deleteGroup = async (groupId) => {
    isLoading.value = true
    try {
      await groupsAPI.deleteGroup(groupId)
      removeGroup(groupId)
    } catch (error) {
      console.error('删除图像组失败:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  // Action: 获取处理进度
  const fetchGroupProgress = async (groupId) => {
    try {
      const progress = await groupsAPI.getGroupProgress(groupId)
      updateProgress(groupId, progress)
      // 更新组状态
      updateGroup(groupId, {
        status: progress.group_status,
        processed_images: progress.completed,
        total_images: progress.total
      })
      return progress
    } catch (error) {
      console.error('获取处理进度失败:', error)
      throw error
    }
  }

  // Action: 获取验证状态
  const fetchValidationStatus = async (groupId) => {
    try {
      const status = await groupsAPI.getValidationStatus(groupId)
      updateValidationStatus(groupId, status)
      return status
    } catch (error) {
      console.error('获取验证状态失败:', error)
      throw error
    }
  }

  // Action: 预处理
  const preprocess = async (groupId, config) => {
    try {
      const result = await groupsAPI.preprocessGroup(groupId, config)
      updateGroup(groupId, { status: 'preprocessing' })
      return result
    } catch (error) {
      console.error('预处理失败:', error)
      throw error
    }
  }

  // Action: 切割单支
  const segmentSlips = async (groupId, config) => {
    try {
      const result = await groupsAPI.segmentSlips(groupId, config)
      updateGroup(groupId, { status: 'segmenting' })
      return result
    } catch (error) {
      console.error('切割单支失败:', error)
      throw error
    }
  }

  // Action: 切割单字
  const segmentChars = async (groupId, config) => {
    try {
      const result = await groupsAPI.segmentChars(groupId, config)
      updateGroup(groupId, { status: 'segmenting' })
      return result
    } catch (error) {
      console.error('切割单字失败:', error)
      throw error
    }
  }

  return {
    // 状态
    groups,
    currentGroup,
    currentGroupImages,
    currentGroupImagesTotal,
    currentGroupImagesPage,
    currentGroupImagesPageSize,
    isLoading,
    imagesLoading,
    progressMap,
    validationStatusMap,

    // 计算属性
    activeGroup,
    totalPages,

    // 方法
    setGroups,
    setCurrentGroup,
    setCurrentGroupImages,
    setCurrentGroupImagesPage,
    setIsLoading,
    setImagesLoading,
    updateProgress,
    clearProgress,
    updateValidationStatus,
    addGroup,
    removeGroup,
    updateGroup,
    addImagesToGroup,
    removeImageFromGroup,

    // Actions
    fetchGroups,
    createGroup,
    fetchGroupDetail,
    uploadImages,
    fetchImages,
    deleteImage,
    deleteGroup,
    fetchGroupProgress,
    fetchValidationStatus,
    preprocess,
    segmentSlips,
    segmentChars
  }
})
