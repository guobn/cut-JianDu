<template>
  <div class="meta-page">
    <div class="meta-page__container">
      <section class="meta-page__header">
        <div class="meta-page__title">切割结果元数据管理</div>
        <div class="meta-page__subtitle">查看与编辑切割结果的描述、事件信息等元数据</div>
      </section>

      <section class="meta-page__section">
        <el-card class="panel-card" shadow="never">
          <div class="toolbar">
            <el-row :gutter="12" align="middle">
              <el-col :xs="24" :sm="12" :md="6">
                <el-select
                  v-model="selectedGroupId"
                  clearable
                  filterable
                  placeholder="选择图像组（可选）"
                  style="width: 100%"
                  :loading="groupsLoading"
                  @change="currentPage = 1"
                >
                  <el-option
                    v-for="group in groups"
                    :key="group.id"
                    :label="group.name"
                    :value="group.id"
                  />
                </el-select>
              </el-col>

              <el-col :xs="24" :sm="12" :md="6">
                <el-input
                  v-model="keyword"
                  clearable
                  placeholder="按原图ID / 编号搜索"
                  @keyup.enter="onSearch"
                />
              </el-col>

              <el-col :xs="12" :sm="8" :md="4">
                <el-select v-model="typeFilter" clearable placeholder="类型" style="width: 100%">
                  <el-option label="单支简牍" value="slip" />
                  <el-option label="单字" value="char" />
                </el-select>
              </el-col>

              <el-col :xs="12" :sm="8" :md="4">
                <el-select v-model="hasMetadataFilter" clearable placeholder="元数据" style="width: 100%">
                  <el-option label="已填写" value="yes" />
                  <el-option label="未填写" value="no" />
                </el-select>
              </el-col>

              <el-col :xs="24" :sm="8" :md="4" class="toolbar__actions-col">
                <el-button :icon="RefreshRight" @click="loadSegments">刷新</el-button>
                <el-button
                  v-if="selectedSegments.length > 0"
                  type="danger"
                  :icon="Delete"
                  @click="handleBatchDelete"
                  :disabled="deleting"
                >
                  删除选中 ({{ selectedSegments.length }})
                </el-button>
              </el-col>
            </el-row>
          </div>

          <el-table
            v-loading="loading"
            :data="pageData"
            size="small"
            class="data-table"
            @row-click="onRowClick"
            @selection-change="handleSelectionChange"
          >
            <el-table-column type="selection" width="55" @click.stop />
            <el-table-column type="index" label="序号" width="60" />
            <el-table-column label="预览" width="100">
              <template #default="{ row }">
                <img
                  :src="row.public_url"
                  :alt="`切割结果 ${row.segment_index}`"
                  class="segment-thumb"
                  loading="lazy"
                  width="60"
                  height="60"
                  @error="handleImageError"
                />
              </template>
            </el-table-column>
            <el-table-column prop="image_id" label="原图ID" min-width="180" show-overflow-tooltip />
            <el-table-column label="简牍编号" width="120">
              <template #default="{ row }">
                <span v-if="row.slip_number">{{ row.slip_number }}</span>
                <span v-else class="metadata-empty">-</span>
              </template>
            </el-table-column>
            <el-table-column label="编号" width="80">
              <template #default="{ row }">
                <el-tag size="small">{{ row.segment_index }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="row.segment_type === 'slip' ? 'primary' : 'success'" size="small">
                  {{ row.segment_type === 'slip' ? '简牍' : '单字' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="尺寸" width="100">
              <template #default="{ row }">
                {{ row.width }} × {{ row.height }}
              </template>
            </el-table-column>
            <el-table-column label="元数据" min-width="200">
              <template #default="{ row }">
                <div v-if="row.metadata" class="metadata-preview">
                  <div v-if="row.metadata.title" class="metadata-preview__title">
                    {{ row.metadata.title }}
                  </div>
                  <div v-if="row.metadata.event_type" class="metadata-preview__type">
                    {{ row.metadata.event_type }}
                  </div>
                </div>
                <span v-else class="metadata-empty">未填写</span>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="160">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" align="center" @click.stop>
              <template #default="{ row }">
                <el-button text @click.stop="onEdit(row)">
                  <el-icon :size="16"><EditPen /></el-icon>
                </el-button>
                <el-button text type="danger" @click.stop="handleDelete(row)">
                  <el-icon :size="16"><Delete /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :total="filteredData.length"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next, jumper"
              background
            />
          </div>
        </el-card>
      </section>
    </div>

    <!-- 编辑元数据对话框 -->
    <el-dialog v-model="editVisible" title="编辑元数据" width="600px" :close-on-click-modal="false">
      <div v-if="currentSegment" class="edit-dialog">
        <div class="edit-dialog__preview">
          <img
            :src="currentSegment.public_url"
            :alt="`切割结果 ${currentSegment.segment_index}`"
            class="edit-dialog__image"
          />
          <div class="edit-dialog__info">
            <div>原图ID: {{ currentSegment.image_id }}</div>
            <div v-if="currentSegment.slip_number">简牍编号: {{ currentSegment.slip_number }}</div>
            <div>编号: {{ currentSegment.segment_index }}</div>
            <div>类型: {{ currentSegment.segment_type === 'slip' ? '简牍' : '单字' }}</div>
            <div>尺寸: {{ currentSegment.width }} × {{ currentSegment.height }}</div>
          </div>
        </div>

        <el-form
          ref="formRef"
          :model="formData"
          label-width="120px"
          label-position="left"
          class="edit-form"
        >
          <el-form-item label="标题">
            <el-input v-model="formData.title" placeholder="简短标题，如：秦令史曰" />
          </el-form-item>

          <el-form-item label="内容描述">
            <el-input
              v-model="formData.content_description"
              type="textarea"
              :rows="3"
              placeholder="详细描述这段简牍或文字的内容"
            />
          </el-form-item>

          <el-form-item label="事件类型">
            <el-select v-model="formData.event_type" clearable placeholder="选择事件类型" style="width: 100%">
              <el-option label="诏令" value="诏令" />
              <el-option label="契约" value="契约" />
              <el-option label="账目" value="账目" />
              <el-option label="书信" value="书信" />
              <el-option label="文书" value="文书" />
              <el-option label="其他" value="其他" />
            </el-select>
          </el-form-item>

          <el-form-item label="事件日期">
            <el-date-picker
              v-model="formData.event_date"
              type="date"
              placeholder="选择日期"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </el-form-item>

          <el-form-item label="地点">
            <el-input v-model="formData.place" placeholder="如：里耶、云梦等" />
          </el-form-item>

          <el-form-item label="涉及人物">
            <el-input
              v-model="peopleInput"
              placeholder="多个用逗号分隔，如：张三,李四"
              @blur="updatePeopleArray"
            />
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSaveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { EditPen, RefreshRight, Delete } from '@element-plus/icons-vue'
import imageProcessingAPI from '@/api/imageProcessing'
import { groupsAPI } from '@/api/groups'

const route = useRoute()

const loading = ref(false)
const groupsLoading = ref(false)
const keyword = ref('')
const typeFilter = ref('')
const hasMetadataFilter = ref('')
const pageSize = ref(10)
const currentPage = ref(1)
const selectedGroupId = ref(null)

const allSegments = ref([])
const groupImageIds = ref({})  // groupId -> Set of image_ids
const editVisible = ref(false)
const currentSegment = ref(null)
const saving = ref(false)
const selectedSegments = ref([])
const deleting = ref(false)
const groups = ref([])

const formData = ref({
  title: '',
  content_description: '',
  event_type: '',
  event_date: '',
  place: '',
  people: []
})

const peopleInput = ref('')

const filteredData = computed(() => {
  let result = allSegments.value

  // 组过滤
  if (selectedGroupId.value) {
    const imageIds = groupImageIds.value[selectedGroupId.value]
    if (imageIds && imageIds.size > 0) {
      result = result.filter((s) => imageIds.has(s.image_id))
    }
  }

  // 关键词搜索
  if (keyword.value.trim()) {
    const kw = keyword.value.trim().toLowerCase()
    result = result.filter(
      (s) =>
        s.image_id.toLowerCase().includes(kw) ||
        String(s.segment_index).includes(kw) ||
        (s.slip_number && s.slip_number.toLowerCase().includes(kw)) ||
        (s.metadata?.title && s.metadata.title.toLowerCase().includes(kw))
    )
  }

  // 类型过滤
  if (typeFilter.value) {
    result = result.filter((s) => s.segment_type === typeFilter.value)
  }

  // 元数据过滤
  if (hasMetadataFilter.value === 'yes') {
    result = result.filter((s) => s.metadata)
  } else if (hasMetadataFilter.value === 'no') {
    result = result.filter((s) => !s.metadata)
  }

  return result
})

const pageData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredData.value.slice(start, start + pageSize.value)
})

onMounted(async () => {
  await Promise.all([loadSegments(), loadGroups()])

  // 如果 URL 中有 segment_id 参数，自动打开编辑对话框
  const segmentId = route.query.segment_id
  if (segmentId) {
    const segment = allSegments.value.find((s) => s.segment_id === segmentId)
    if (segment) {
      // 延迟一下确保列表已渲染
      setTimeout(() => {
        onEdit(segment)
      }, 300)
    } else {
      // 如果列表中没有，尝试单独获取
      try {
        const seg = await imageProcessingAPI.getSegment(segmentId)
        onEdit(seg)
      } catch (error) {
        ElMessage.warning('未找到该切割结果')
      }
    }
  }
})

// 监听路由变化（如果用户在同一页面内切换 segment_id）
watch(() => route.query.segment_id, async (newSegmentId) => {
  if (newSegmentId && !editVisible.value) {
    const segment = allSegments.value.find((s) => s.segment_id === newSegmentId)
    if (segment) {
      onEdit(segment)
    } else {
      try {
        const seg = await imageProcessingAPI.getSegment(newSegmentId)
        onEdit(seg)
      } catch (error) {
        ElMessage.warning('未找到该切割结果')
      }
    }
  }
})

// 监听组选择变化，加载该组的图片
watch(selectedGroupId, async (newGroupId) => {
  if (newGroupId) {
    await loadGroupImages(newGroupId)
  }
  currentPage.value = 1
})

async function loadSegments() {
  try {
    loading.value = true
    const segments = await imageProcessingAPI.listSegments({ limit: 100 })
    allSegments.value = segments
    ElMessage.success(`已加载 ${segments.length} 条切割结果`)
  } catch (error) {
    console.error('加载切割结果失败:', error)
    handleApiError(`加载失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

async function loadGroups() {
  try {
    groupsLoading.value = true
    const groupsData = await groupsAPI.getGroups()
    groups.value = groupsData || []
  } catch (error) {
    console.error('加载图像组失败:', error)
  } finally {
    groupsLoading.value = false
  }
}

async function loadGroupImages(groupId) {
  if (!groupId) {
    groupImageIds.value[groupId] = new Set()
    return
  }
  if (groupImageIds.value[groupId]) {
    return  // Already loaded
  }
  try {
    const response = await groupsAPI.getGroupImages(groupId, 1, 1000)
    const images = response.items || response || []
    groupImageIds.value[groupId] = new Set(images.map(img => img.image_id || img.id))
  } catch (error) {
    console.error('加载组图片失败:', error)
    groupImageIds.value[groupId] = new Set()
  }
}

function onSearch() {
  currentPage.value = 1
}

function onRowClick(row) {
  onEdit(row)
}

function onEdit(row) {
  currentSegment.value = row
  formData.value = {
    title: row.metadata?.title || '',
    content_description: row.metadata?.content_description || '',
    event_type: row.metadata?.event_type || '',
    event_date: row.metadata?.event_date || '',
    place: row.metadata?.place || '',
    people: row.metadata?.people || []
  }
  peopleInput.value = Array.isArray(formData.value.people) ? formData.value.people.join(',') : ''
  editVisible.value = true
}

function updatePeopleArray() {
  if (peopleInput.value.trim()) {
    formData.value.people = peopleInput.value
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
  } else {
    formData.value.people = []
  }
}

async function onSaveEdit() {
  if (!currentSegment.value) return

  try {
    saving.value = true
    updatePeopleArray()

    // 移除空值
    const metadata = { ...formData.value }
    Object.keys(metadata).forEach((key) => {
      if (metadata[key] === '' || (Array.isArray(metadata[key]) && metadata[key].length === 0)) {
        delete metadata[key]
      }
    })

    await imageProcessingAPI.upsertSegmentMetadata(currentSegment.value.segment_id, metadata)

    ElMessage.success('元数据已保存')
    editVisible.value = false

    // 重新加载列表以更新显示
    await loadSegments()
  } catch (error) {
    console.error('保存元数据失败:', error)
    handleApiError(`保存失败: ${error.message}`)
  } finally {
    saving.value = false
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function handleImageError(event) {
  event.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2Y1ZjVmNSIvPjx0ZXh0IHg9IjUwIiB5PSI1NSIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSI+5Zu+54mHPC90ZXh0Pjwvc3ZnPg=='
}

function handleSelectionChange(selection) {
  selectedSegments.value = selection
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除切割结果 "${row.segment_id}" 吗？此操作将同时删除文件和相关元数据，且无法恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
        dangerouslyUseHTMLString: false
      }
    )

    deleting.value = true
    await imageProcessingAPI.deleteSegment(row.segment_id)
    ElMessage.success('删除成功')
    
    // 从列表中移除
    const index = allSegments.value.findIndex((s) => s.segment_id === row.segment_id)
    if (index !== -1) {
      allSegments.value.splice(index, 1)
    }
    
    // 如果当前页没有数据了，返回上一页
    if (pageData.value.length === 0 && currentPage.value > 1) {
      currentPage.value--
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      handleApiError(`删除失败: ${error.message || '未知错误'}`)
    }
  } finally {
    deleting.value = false
  }
}

async function handleBatchDelete() {
  if (selectedSegments.value.length === 0) {
    ElMessage.warning('请先选择要删除的切割结果')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedSegments.value.length} 个切割结果吗？此操作将同时删除文件和相关元数据，且无法恢复。`,
      '确认批量删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    deleting.value = true
    const segmentIds = selectedSegments.value.map((s) => s.segment_id)
    const result = await imageProcessingAPI.deleteSegments(segmentIds)
    
    if (result.error_count > 0) {
      ElMessage.warning(`成功删除 ${result.success_count} 个，失败 ${result.error_count} 个`)
    } else {
      ElMessage.success(`成功删除 ${result.success_count} 个切割结果`)
    }
    
    // 重新加载列表
    await loadSegments()
    
    // 清空选择
    selectedSegments.value = []
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      handleApiError(`批量删除失败: ${error.message || '未知错误'}`)
    }
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped>
.meta-page {
  width: 100%;
}

.meta-page__container {
  max-width: 1400px;
  margin: 0 auto;
}

.meta-page__header {
  padding: 6px 2px 8px;
}

.meta-page__title {
  font-size: 22px;
  font-weight: 800;
  color: #1f2d3d;
  letter-spacing: 0.6px;
}

.meta-page__subtitle {
  margin-top: 6px;
  font-size: 12px;
  color: rgba(31, 45, 61, 0.62);
  letter-spacing: 0.35px;
}

.meta-page__section {
  margin-top: 18px;
}

.panel-card {
  border-radius: 12px;
  border: 1px solid rgba(31, 45, 61, 0.10);
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 10px 20px rgba(17, 24, 39, 0.05);
}

.toolbar {
  margin-bottom: 14px;
}

.toolbar__actions-col {
  display: flex;
  justify-content: flex-end;
}

.data-table {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(31, 45, 61, 0.08);
}

:deep(.el-table th.el-table__cell) {
  background: rgba(31, 45, 61, 0.03);
}

:deep(.el-table tbody tr) {
  cursor: pointer;
}

:deep(.el-table tbody tr:hover) {
  background-color: rgba(64, 158, 255, 0.05);
}

.segment-thumb {
  width: 60px;
  height: 60px;
  object-fit: cover;
  background: #f5f5f5;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(31, 45, 61, 0.1);
  flex-shrink: 0;
}

.metadata-preview {
  font-size: 12px;
}

.metadata-preview__title {
  font-weight: 600;
  color: #1f2d3d;
  margin-bottom: 4px;
}

.metadata-preview__type {
  color: rgba(31, 45, 61, 0.6);
}

.metadata-empty {
  color: rgba(31, 45, 61, 0.4);
  font-style: italic;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.edit-dialog {
  padding: 10px 0;
}

.edit-dialog__preview {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  padding: 12px;
  background: rgba(31, 45, 61, 0.03);
  border-radius: 8px;
}

.edit-dialog__image {
  width: 120px;
  height: 120px;
  object-fit: contain;
  background: white;
  border-radius: 4px;
  border: 1px solid rgba(31, 45, 61, 0.1);
  flex-shrink: 0;
}

.edit-dialog__info {
  flex: 1;
  font-size: 12px;
  color: rgba(31, 45, 61, 0.7);
  line-height: 1.8;
}

.edit-form {
  margin-top: 10px;
}
</style>
