<template>
  <div class="slip-gallery-page">
    <div class="slip-gallery-page__container">
      <section class="slip-gallery-page__header">
        <div class="slip-gallery-page__title">简牍图库</div>
        <div class="slip-gallery-page__subtitle">查看与管理简牍切割结果及元数据</div>
      </section>

      <section class="slip-gallery-page__section">
        <el-card class="panel-card" shadow="never">
          <!-- 顶部工具栏 -->
          <div class="toolbar">
            <el-row :gutter="12" align="middle">
              <el-col :xs="24" :sm="10" :md="6">
                <el-select
                  v-model="selectedGroupId"
                  filterable
                  placeholder="选择图像组"
                  style="width: 100%"
                  :loading="groupsLoading"
                  @change="onGroupChange"
                >
                  <el-option
                    v-for="group in groups"
                    :key="group.id"
                    :label="group.name"
                    :value="group.id"
                  />
                </el-select>
              </el-col>

              <el-col :xs="24" :sm="14" :md="6">
                <div class="view-toggle">
                  <el-button-group>
                    <el-button :type="viewMode === 'grid' ? 'primary' : ''" @click="viewMode = 'grid'">
                      <el-icon><Grid /></el-icon>
                    </el-button>
                    <el-button :type="viewMode === 'list' ? 'primary' : ''" @click="viewMode = 'list'">
                      <el-icon><List /></el-icon>
                    </el-button>
                  </el-button-group>
                </div>
              </el-col>

              <el-col :xs="24" :md="12" class="toolbar__actions">
                <el-button @click="handleExport">
                  <el-icon><Download /></el-icon>
                  导出
                </el-button>
                <el-button
                  v-if="selectedSlips.length > 0"
                  type="primary"
                  @click="showBatchDialog = true"
                >
                  批量编辑 ({{ selectedSlips.length }})
                </el-button>
              </el-col>
            </el-row>
          </div>

          <!-- 筛选栏 -->
          <div class="filter-bar">
            <el-row :gutter="12" align="middle">
              <el-col :xs="24" :sm="8" :md="6">
                <el-select v-model="typeFilter" clearable placeholder="类型" style="width: 100%">
                  <el-option label="简牍" value="slip" />
                  <el-option label="单字" value="char" />
                  <el-option label="全部" value="all" />
                </el-select>
              </el-col>

              <el-col :xs="24" :sm="8" :md="6">
                <el-select v-model="completenessFilter" clearable placeholder="元数据状态" style="width: 100%">
                  <el-option label="已填写" value="filled" />
                  <el-option label="未填写" value="unfilled" />
                  <el-option label="全部" value="all" />
                </el-select>
              </el-col>

              <el-col :xs="24" :sm="8" :md="6">
                <el-input
                  v-model="keywordFilter"
                  clearable
                  placeholder="搜索简牍编号/标题"
                  @keyup.enter="onSearch"
                >
                  <template #prefix>
                    <el-icon><Search /></el-icon>
                  </template>
                </el-input>
              </el-col>
            </el-row>
          </div>

          <!-- 加载状态 -->
          <div v-if="loading" class="loading-container">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>加载简牍数据...</span>
          </div>

          <!-- 无数据提示 -->
          <el-empty v-else-if="!selectedGroupId" description="请先选择图像组" />
          <el-empty v-else-if="filteredData.length === 0" description="暂无数据" />

          <!-- 网格视图 -->
          <div v-else-if="viewMode === 'grid'" class="slips-grid">
            <el-checkbox-group v-model="selectedSlips">
              <el-row :gutter="16">
                <el-col
                  v-for="item in paginatedData"
                  :key="item.segment_id"
                  :xs="24"
                  :sm="12"
                  :md="8"
                  :lg="6"
                >
                  <div class="slip-card" @click="openDetail(item)">
                    <el-checkbox :value="item.segment_id" class="slip-card__checkbox" @click.stop>
                      <template #default>
                        <div class="slip-card__inner">
                          <div class="slip-card__thumb">
                            <img
                              :src="item.public_url"
                              :alt="item.slip_number || item.segment_index"
                              @error="handleImageError"
                              loading="lazy"
                            />
                            <div class="slip-card__type-badge">
                              <el-tag size="small" :type="item.segment_type === 'slip' ? 'primary' : 'success'">
                                {{ item.segment_type === 'slip' ? '简牍' : '单字' }}
                              </el-tag>
                            </div>
                          </div>
                          <div class="slip-card__info">
                            <div class="slip-card__number">
                              {{ item.slip_number || `编号: ${item.segment_index}` }}
                            </div>
                            <div class="slip-card__meta">
                              <el-tag v-if="item.metadata && Object.keys(item.metadata).length > 0" type="success" size="small">
                                已填写
                              </el-tag>
                              <el-tag v-else type="info" size="small">
                                未填写
                              </el-tag>
                            </div>
                          </div>
                        </div>
                      </template>
                    </el-checkbox>
                  </div>
                </el-col>
              </el-row>
            </el-checkbox-group>
          </div>

          <!-- 列表视图 -->
          <div v-else class="slips-table">
            <el-table
              :data="paginatedData"
              @selection-change="handleSelectionChange"
              @row-click="openDetail"
              v-loading="loading"
            >
              <el-table-column type="selection" width="55" @click.stop />
              <el-table-column type="index" label="序号" width="60" />
              <el-table-column label="预览" width="100">
                <template #default="{ row }">
                  <img
                    :src="row.public_url"
                    :alt="row.slip_number || row.segment_index"
                    class="slip-thumb"
                    loading="lazy"
                    @error="handleImageError"
                  />
                </template>
              </el-table-column>
              <el-table-column prop="segment_id" label="ID" min-width="120" show-overflow-tooltip />
              <el-table-column label="编号" width="120">
                <template #default="{ row }">
                  <span v-if="row.slip_number">{{ row.slip_number }}</span>
                  <span v-else class="metadata-empty">-</span>
                </template>
              </el-table-column>
              <el-table-column label="类型" width="100">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.segment_type === 'slip' ? 'primary' : 'success'">
                    {{ row.segment_type === 'slip' ? '简牍' : '单字' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="元数据状态" width="120">
                <template #default="{ row }">
                  <el-tag v-if="row.metadata && Object.keys(row.metadata).length > 0" type="success" size="small">
                    已填写
                  </el-tag>
                  <el-tag v-else type="info" size="small">
                    未填写
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="创建时间" width="160">
                <template #default="{ row }">
                  {{ formatDate(row.created_at) }}
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 分页 -->
          <div v-if="filteredData.length > 0" class="pager">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :total="filteredData.length"
              :page-sizes="[12, 24, 48, 96]"
              layout="total, sizes, prev, pager, next, jumper"
              background
            />
          </div>
        </el-card>
      </section>
    </div>

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="detailDrawerVisible"
      title="简牍详情"
      size="600px"
      :close-on-click-modal="false"
    >
      <div v-if="currentSlip" class="detail-drawer">
        <div class="detail-drawer__image">
          <img
            :src="currentSlip.public_url"
            :alt="currentSlip.slip_number || currentSlip.segment_index"
            @error="handleImageError"
          />
        </div>

        <div class="detail-drawer__info">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="ID">
              {{ currentSlip.segment_id }}
            </el-descriptions-item>
            <el-descriptions-item label="简牍编号">
              {{ currentSlip.slip_number || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="类型">
              {{ currentSlip.segment_type === 'slip' ? '简牍' : '单字' }}
            </el-descriptions-item>
            <el-descriptions-item label="尺寸">
              {{ currentSlip.width }} × {{ currentSlip.height }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatDate(currentSlip.created_at) }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <el-divider>元数据</el-divider>

        <el-form
          ref="formRef"
          :model="formData"
          label-width="100px"
          label-position="left"
        >
          <el-form-item label="标题">
            <el-input v-model="formData.title" placeholder="简短标题" />
          </el-form-item>

          <el-form-item label="内容描述">
            <el-input
              v-model="formData.content_description"
              type="textarea"
              :rows="3"
              placeholder="详细描述内容"
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
              placeholder="多个用逗号分隔"
              @blur="updatePeopleArray"
            />
          </el-form-item>
        </el-form>

        <div class="detail-drawer__actions">
          <el-button @click="detailDrawerVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="onSaveMetadata">保存</el-button>
        </div>
      </div>
    </el-drawer>

    <!-- 批量编辑对话框 -->
    <el-dialog v-model="showBatchDialog" title="批量编辑元数据" width="500px">
      <el-form :model="batchForm" label-width="100px" label-position="left">
        <el-form-item label="事件类型">
          <el-select v-model="batchForm.event_type" clearable placeholder="选择事件类型" style="width: 100%">
            <el-option label="诏令" value="诏令" />
            <el-option label="契约" value="契约" />
            <el-option label="账目" value="账目" />
            <el-option label="书信" value="书信" />
            <el-option label="文书" value="文书" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>

        <el-form-item label="地点">
          <el-input v-model="batchForm.place" placeholder="如：里耶、云梦等" />
        </el-form-item>

        <el-form-item label="事件日期">
          <el-date-picker
            v-model="batchForm.event_date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showBatchDialog = false">取消</el-button>
        <el-button type="primary" :loading="batchSaving" @click="onBatchSave">
          确认更新 ({{ selectedSlips.length }} 条)
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Grid, List, Download, Search, Loading } from '@element-plus/icons-vue'
import { groupsAPI } from '@/api/groups'
import slipsAPI from '@/api/slips'

// 状态
const groups = ref([])
const groupsLoading = ref(false)
const selectedGroupId = ref(null)
const slips = ref([])
const loading = ref(false)
const viewMode = ref('grid')
const selectedSlips = ref([])
const currentPage = ref(1)
const pageSize = ref(24)

// 筛选
const typeFilter = ref('all')
const completenessFilter = ref('all')
const keywordFilter = ref('')

// 详情抽屉
const detailDrawerVisible = ref(false)
const currentSlip = ref(null)
const saving = ref(false)
const formRef = ref(null)
const formData = ref({
  title: '',
  content_description: '',
  event_type: '',
  event_date: '',
  place: '',
  people: []
})
const peopleInput = ref('')

// 批量编辑
const showBatchDialog = ref(false)
const batchSaving = ref(false)
const batchForm = ref({
  event_type: '',
  event_date: '',
  place: ''
})

// 计算属性
const filteredData = computed(() => {
  let result = slips.value

  // 类型过滤
  if (typeFilter.value && typeFilter.value !== 'all') {
    result = result.filter(s => s.segment_type === typeFilter.value)
  }

  // 元数据完整性过滤
  if (completenessFilter.value === 'filled') {
    result = result.filter(s => s.metadata && Object.keys(s.metadata).length > 0)
  } else if (completenessFilter.value === 'unfilled') {
    result = result.filter(s => !s.metadata || Object.keys(s.metadata).length === 0)
  }

  // 关键词搜索
  if (keywordFilter.value.trim()) {
    const kw = keywordFilter.value.trim().toLowerCase()
    result = result.filter(s =>
      (s.slip_number && s.slip_number.toLowerCase().includes(kw)) ||
      String(s.segment_index).includes(kw) ||
      (s.metadata?.title && s.metadata.title.toLowerCase().includes(kw)) ||
      (s.metadata?.event_type && s.metadata.event_type.toLowerCase().includes(kw))
    )
  }

  return result
})

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredData.value.slice(start, start + pageSize.value)
})

// 初始化
onMounted(async () => {
  await loadGroups()
})

// 加载图像组列表
async function loadGroups() {
  try {
    groupsLoading.value = true
    const data = await groupsAPI.getGroups()
    groups.value = data || []
  } catch (error) {
    console.error('加载图像组失败:', error)
    ElMessage.error('加载图像组失败')
  } finally {
    groupsLoading.value = false
  }
}

// 组选择变化
async function onGroupChange(groupId) {
  if (!groupId) {
    slips.value = []
    return
  }
  await loadSlips(groupId)
}

// 加载简牍列表
async function loadSlips(groupId) {
  try {
    loading.value = true
    const data = await slipsAPI.getSlipsByGroup(groupId)
    slips.value = Array.isArray(data) ? data : (data.items || [])
    selectedSlips.value = []
    currentPage.value = 1
  } catch (error) {
    console.error('加载简牍列表失败:', error)
    ElMessage.error('加载简牍列表失败')
  } finally {
    loading.value = false
  }
}

// 打开详情
function openDetail(item) {
  currentSlip.value = item
  formData.value = {
    title: item.metadata?.title || '',
    content_description: item.metadata?.content_description || '',
    event_type: item.metadata?.event_type || '',
    event_date: item.metadata?.event_date || '',
    place: item.metadata?.place || '',
    people: item.metadata?.people || []
  }
  peopleInput.value = Array.isArray(formData.value.people) ? formData.value.people.join(',') : ''
  detailDrawerVisible.value = true
}

// 保存元数据
async function onSaveMetadata() {
  if (!currentSlip.value) return

  try {
    saving.value = true
    updatePeopleArray()

    // 清理空值
    const metadata = { ...formData.value }
    Object.keys(metadata).forEach(key => {
      if (metadata[key] === '' || (Array.isArray(metadata[key]) && metadata[key].length === 0)) {
        delete metadata[key]
      }
    })

    await slipsAPI.updateSlipMetadata(currentSlip.value.segment_id, metadata)

    // 更新本地数据
    const index = slips.value.findIndex(s => s.segment_id === currentSlip.value.segment_id)
    if (index !== -1) {
      slips.value[index].metadata = { ...slips.value[index].metadata, ...metadata }
    }

    ElMessage.success('元数据已保存')
    detailDrawerVisible.value = false
  } catch (error) {
    console.error('保存元数据失败:', error)
    ElMessage.error(`保存失败: ${error.message}`)
  } finally {
    saving.value = false
  }
}

// 批量保存
async function onBatchSave() {
  if (selectedSlips.value.length === 0) {
    ElMessage.warning('请先选择要编辑的简牍')
    return
  }

  try {
    batchSaving.value = true

    // 清理空值
    const metadata = { ...batchForm.value }
    Object.keys(metadata).forEach(key => {
      if (metadata[key] === '') {
        delete metadata[key]
      }
    })

    if (Object.keys(metadata).length === 0) {
      ElMessage.warning('请至少填写一项元数据')
      return
    }

    await slipsAPI.batchUpdateSlipMetadata(selectedSlips.value, metadata)

    // 更新本地数据
    selectedSlips.value.forEach(slipId => {
      const index = slips.value.findIndex(s => s.segment_id === slipId)
      if (index !== -1) {
        slips.value[index].metadata = { ...slips.value[index].metadata, ...metadata }
      }
    })

    ElMessage.success(`成功更新 ${selectedSlips.value.length} 条元数据`)
    showBatchDialog.value = false
    selectedSlips.value = []

    // 重置批量表单
    batchForm.value = { event_type: '', event_date: '', place: '' }
  } catch (error) {
    console.error('批量保存失败:', error)
    ElMessage.error(`批量保存失败: ${error.message}`)
  } finally {
    batchSaving.value = false
  }
}

// 导出
function handleExport() {
  ElMessage.info('导出功能开发中')
}

// 搜索
function onSearch() {
  currentPage.value = 1
}

// 选择变化
function handleSelectionChange(selection) {
  selectedSlips.value = selection.map(s => s.segment_id)
}

// 更新人物数组
function updatePeopleArray() {
  if (peopleInput.value.trim()) {
    formData.value.people = peopleInput.value
      .split(',')
      .map(s => s.trim())
      .filter(Boolean)
  } else {
    formData.value.people = []
  }
}

// 格式化日期
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

// 图片加载失败处理
function handleImageError(event) {
  event.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2Y1ZjVmNSIvPjx0ZXh0IHg9IjUwIiB5PSI1NSIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSI+5Zu+54mHPC90ZXh0Pjwvc3ZnPg=='
}

// 监听筛选器变化，重置页码
watch([typeFilter, completenessFilter, keywordFilter], () => {
  currentPage.value = 1
})
</script>

<style scoped>
.slip-gallery-page {
  width: 100%;
}

.slip-gallery-page__container {
  max-width: 1600px;
  margin: 0 auto;
}

.slip-gallery-page__header {
  padding: 6px 2px 8px;
}

.slip-gallery-page__title {
  font-size: 22px;
  font-weight: 800;
  color: #1f2d3d;
  letter-spacing: 0.6px;
}

.slip-gallery-page__subtitle {
  margin-top: 6px;
  font-size: 12px;
  color: rgba(31, 45, 61, 0.62);
  letter-spacing: 0.35px;
}

.slip-gallery-page__section {
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

.toolbar__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.view-toggle {
  display: flex;
}

.filter-bar {
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(31, 45, 61, 0.03);
  border-radius: 8px;
}

.loading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 60px 0;
  color: rgba(31, 45, 61, 0.6);
}

.slips-grid {
  min-height: 300px;
}

.slip-card {
  margin-bottom: 16px;
  border: 1px solid rgba(31, 45, 61, 0.1);
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s;
  cursor: pointer;
}

.slip-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.slip-card__checkbox {
  display: block;
  width: 100%;
}

.slip-card__checkbox :deep(.el-checkbox__input) {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 1;
}

.slip-card__inner {
  padding: 0;
}

.slip-card__thumb {
  position: relative;
  width: 100%;
  height: 160px;
  background: #f5f5f5;
  overflow: hidden;
}

.slip-card__thumb img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.slip-card__type-badge {
  position: absolute;
  top: 8px;
  right: 8px;
}

.slip-card__info {
  padding: 12px;
}

.slip-card__number {
  font-size: 14px;
  font-weight: 600;
  color: #1f2d3d;
  margin-bottom: 6px;
}

.slip-card__meta {
  display: flex;
  gap: 6px;
}

.slip-thumb {
  width: 60px;
  height: 60px;
  object-fit: cover;
  background: #f5f5f5;
  border-radius: 4px;
}

.metadata-empty {
  color: rgba(31, 45, 61, 0.4);
  font-style: italic;
}

.slips-table {
  min-height: 300px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.detail-drawer {
  padding: 0 4px;
}

.detail-drawer__image {
  width: 100%;
  max-height: 300px;
  background: #f5f5f5;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.detail-drawer__image img {
  max-width: 100%;
  max-height: 300px;
  object-fit: contain;
}

.detail-drawer__info {
  margin-bottom: 16px;
}

.detail-drawer__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}
</style>
