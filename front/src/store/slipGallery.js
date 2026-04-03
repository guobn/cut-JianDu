/**
 * SlipGallery 状态管理 Store
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import slipsAPI from '@/api/slips'

export const useSlipGalleryStore = defineStore('slipGallery', () => {
  // 状态
  const currentGroup = ref(null)
  const slips = ref([])
  const chars = ref({})  // slipId -> char[]
  const filters = ref({
    type: 'all',         // 'slip' | 'char' | 'all'
    completeness: 'all',  // 'filled' | 'unfilled' | 'all'
    keyword: ''
  })
  const viewMode = ref('grid')  // 'grid' | 'list'
  const loading = ref(false)
  const charsLoading = ref({})  // slipId -> boolean
  const selectedSlips = ref([])
  const currentSlip = ref(null)  // 当前查看的简牍详情

  // 计算属性
  const filteredSlips = computed(() => {
    let result = slips.value

    // 类型过滤
    if (filters.value.type === 'slip') {
      result = result.filter(s => s.segment_type === 'slip')
    } else if (filters.value.type === 'char') {
      result = result.filter(s => s.segment_type === 'char')
    }

    // 元数据完整性过滤
    if (filters.value.completeness === 'filled') {
      result = result.filter(s => s.metadata && Object.keys(s.metadata).length > 0)
    } else if (filters.value.completeness === 'unfilled') {
      result = result.filter(s => !s.metadata || Object.keys(s.metadata).length === 0)
    }

    // 关键词搜索
    if (filters.value.keyword.trim()) {
      const kw = filters.value.keyword.trim().toLowerCase()
      result = result.filter(s =>
        (s.slip_number && s.slip_number.toLowerCase().includes(kw)) ||
        String(s.segment_index).includes(kw) ||
        (s.metadata?.title && s.metadata.title.toLowerCase().includes(kw)) ||
        (s.metadata?.event_type && s.metadata.event_type.toLowerCase().includes(kw))
      )
    }

    return result
  })

  const hasChars = (slipId) => {
    return chars.value[slipId] && chars.value[slipId].length > 0
  }

  const isCharsLoading = (slipId) => {
    return charsLoading.value[slipId] || false
  }

  // Actions

  /**
   * 按组获取简牍列表
   * @param {string} groupId - 组ID
   */
  async function fetchSlipsByGroup(groupId) {
    try {
      loading.value = true
      currentGroup.value = groupId
      const data = await slipsAPI.getSlipsByGroup(groupId)
      slips.value = Array.isArray(data) ? data : (data.items || [])
    } catch (error) {
      console.error('获取简牍列表失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取指定简牍下的单字
   * @param {string} slipId - 简牍ID
   * @param {string} groupId - 组ID
   */
  async function fetchChars(slipId, groupId) {
    try {
      charsLoading.value[slipId] = true
      const data = await slipsAPI.getCharsBySlip(slipId, groupId)
      chars.value[slipId] = Array.isArray(data) ? data : (data.items || [])
    } catch (error) {
      console.error('获取单字列表失败:', error)
      chars.value[slipId] = []
      throw error
    } finally {
      charsLoading.value[slipId] = false
    }
  }

  /**
   * 获取简牍详情
   * @param {string} slipId - 简牍ID
   */
  async function fetchSlipDetail(slipId) {
    try {
      const data = await slipsAPI.getSlipMetadata(slipId)
      currentSlip.value = data
      return data
    } catch (error) {
      console.error('获取简牍详情失败:', error)
      throw error
    }
  }

  /**
   * 更新简牍元数据
   * @param {string} slipId - 简牍ID
   * @param {Object} metadata - 元数据
   */
  async function updateMetadata(slipId, metadata) {
    try {
      await slipsAPI.updateSlipMetadata(slipId, metadata)
      // 更新本地数据
      const index = slips.value.findIndex(s => s.segment_id === slipId)
      if (index !== -1) {
        slips.value[index].metadata = { ...slips.value[index].metadata, ...metadata }
      }
      if (currentSlip.value && currentSlip.value.segment_id === slipId) {
        currentSlip.value.metadata = { ...currentSlip.value.metadata, ...metadata }
      }
    } catch (error) {
      console.error('更新元数据失败:', error)
      throw error
    }
  }

  /**
   * 批量更新简牍元数据
   * @param {string[]} slipIds - 简牍ID数组
   * @param {Object} metadata - 要更新的元数据
   */
  async function batchUpdateMetadata(slipIds, metadata) {
    try {
      await slipsAPI.batchUpdateSlipMetadata(slipIds, metadata)
      // 更新本地数据
      slipIds.forEach(slipId => {
        const index = slips.value.findIndex(s => s.segment_id === slipId)
        if (index !== -1) {
          slips.value[index].metadata = { ...slips.value[index].metadata, ...metadata }
        }
      })
      // 清空选择
      selectedSlips.value = []
    } catch (error) {
      console.error('批量更新元数据失败:', error)
      throw error
    }
  }

  /**
   * 删除简牍
   * @param {string} slipId - 简牍ID
   */
  async function deleteSlip(slipId) {
    try {
      await slipsAPI.deleteSlip(slipId)
      // 从列表中移除
      const index = slips.value.findIndex(s => s.segment_id === slipId)
      if (index !== -1) {
        slips.value.splice(index, 1)
      }
      // 清空详情
      if (currentSlip.value && currentSlip.value.segment_id === slipId) {
        currentSlip.value = null
      }
    } catch (error) {
      console.error('删除简牍失败:', error)
      throw error
    }
  }

  /**
   * 清除数据
   */
  function clearAll() {
    currentGroup.value = null
    slips.value = []
    chars.value = {}
    filters.value = { type: 'all', completeness: 'all', keyword: '' }
    viewMode.value = 'grid'
    selectedSlips.value = []
    currentSlip.value = null
  }

  /**
   * 切换视图模式
   */
  function toggleViewMode() {
    viewMode.value = viewMode.value === 'grid' ? 'list' : 'grid'
  }

  /**
   * 设置筛选条件
   */
  function setFilter(key, value) {
    filters.value[key] = value
  }

  return {
    // 状态
    currentGroup,
    slips,
    chars,
    filters,
    viewMode,
    loading,
    charsLoading,
    selectedSlips,
    currentSlip,

    // 计算属性
    filteredSlips,
    hasChars,
    isCharsLoading,

    // Actions
    fetchSlipsByGroup,
    fetchChars,
    fetchSlipDetail,
    updateMetadata,
    batchUpdateMetadata,
    deleteSlip,
    clearAll,
    toggleViewMode,
    setFilter
  }
})
