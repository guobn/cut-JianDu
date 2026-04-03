<template>
  <div class="image-group-page">
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <h1>图像组管理</h1>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>
        新建图像组
      </el-button>
    </div>

    <!-- 图像组列表 -->
    <div class="groups-container">
      <el-empty v-if="groupStore.groups.length === 0 && !groupStore.isLoading" description="暂无图像组" />
      <div v-else class="groups-grid">
        <div v-for="group in groupStore.groups" :key="group.id" class="group-card">
          <!-- 缩略图 -->
          <div class="group-thumbnail">
            <template v-if="group.thumbnail_url">
              <img
                :src="getFullImageUrl(group.thumbnail_url)"
                :alt="group.name"
                @error="handleImageError"
              />
            </template>
            <template v-else>
              <div class="thumbnail-placeholder">
                <el-icon><Picture /></el-icon>
              </div>
            </template>
          </div>

          <!-- 组信息 -->
          <div class="group-info">
            <h3>{{ group.name }}</h3>
            <p class="description">{{ group.description || '暂无描述' }}</p>

            <!-- 状态和数量 -->
            <div class="meta">
              <el-tag :type="getStatusType(group.status)">{{ getStatusLabel(group.status) }}</el-tag>
              <span class="count">{{ group.total_images || 0 }} 张图片</span>
            </div>

            <!-- 进度条 -->
            <el-progress
              :percentage="getProgressPercentage(group)"
              :color="getProgressColor"
            />

            <!-- 操作按钮 -->
            <div class="actions">
              <el-button size="small" @click="handleImportImages(group)">导入图片</el-button>
              <el-button size="small" @click="handlePreprocess(group)" :disabled="(group.total_images || 0) === 0">预处理</el-button>
              <el-button size="small" @click="handleSegmentSlips(group)" :disabled="(group.total_images || 0) === 0">切割</el-button>
              <el-button size="small" type="primary" @click="router.push({ path: '/detail', query: { groupId: group.id } })">详情</el-button>
              <el-button size="small" type="danger" @click="handleDelete(group)">删除</el-button>
            </div>
          </div>

          <!-- 展开按钮 -->
          <div class="expand-btn" :class="{ expanded: expandedGroupId === group.id }" @click="toggleGroupExpand(group)">
            <el-icon><ArrowDown /></el-icon>
          </div>
        </div>
      </div>
    </div>

    <!-- 展开的组内图片列表 -->
    <div v-if="expandedGroupId" class="expanded-group">
      <div class="group-images">
        <div class="images-header">
          <h3>{{ expandedGroupName }} - 图片列表</h3>
          <el-button size="small" @click="closeExpandedGroup">关闭</el-button>
        </div>

        <!-- 图片操作栏 -->
        <div class="images-toolbar">
          <el-button size="small" type="danger" :disabled="!selectedImages.length" @click="handleBatchDeleteImages">
            删除选中 ({{ selectedImages.length }})
          </el-button>
          <span class="images-count">共 {{ groupStore.currentGroupImagesTotal }} 张</span>
        </div>

        <!-- 图片网格 -->
        <div v-if="groupStore.imagesLoading" class="images-loading">
          <el-icon class="is-loading"><Loading /></el-icon>
          加载中...
        </div>
        <div v-else-if="groupStore.currentGroupImages.length === 0" class="images-empty">
          暂无图片
        </div>
        <div v-else class="images-grid">
          <div
            v-for="image in groupStore.currentGroupImages"
            :key="image.id"
            class="image-item"
            :class="{ selected: selectedImages.includes(image.id) }"
            @click="toggleImageSelection(image.id)"
          >
            <div class="image-checkbox" v-if="selectedImages.includes(image.id)">
              <el-icon><Check /></el-icon>
            </div>
            <img
              :src="getFullImageUrl(image.thumbnail_url)"
              :alt="image.filename"
              @error="handleImageError"
            />
            <p class="filename" :title="image.filename">{{ image.filename }}</p>
            <p class="size">{{ formatFileSize(image.file_size) }}</p>
          </div>
        </div>

        <!-- 分页 -->
        <div class="images-pagination" v-if="groupStore.totalPages > 1">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="groupStore.currentGroupImagesPageSize"
            :total="groupStore.currentGroupImagesTotal"
            layout="prev, pager, next"
            @current-change="handlePageChange"
          />
        </div>
      </div>
    </div>

    <!-- 创建图像组对话框 -->
    <el-dialog v-model="showCreateDialog" title="新建图像组" width="500px" @close="resetCreateForm">
      <el-form :model="createForm" label-width="100px" :rules="createFormRules" ref="createFormRef">
        <el-form-item label="组名称" prop="name">
          <el-input v-model="createForm.name" placeholder="请输入组名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" rows="3" placeholder="可选" />
        </el-form-item>
        <el-form-item label="出土地点">
          <el-input v-model="createForm.source_site" placeholder="可选" />
        </el-form-item>
        <el-form-item label="时代断代">
          <el-input v-model="createForm.period" placeholder="可选" />
        </el-form-item>
        <el-form-item label="材质">
          <el-select v-model="createForm.material" placeholder="可选" clearable>
            <el-option label="竹" value="竹" />
            <el-option label="木" value="木" />
          </el-select>
        </el-form-item>
        <el-form-item label="收藏机构">
          <el-input v-model="createForm.collection" placeholder="可选" />
        </el-form-item>
        <el-form-item label="发掘年份">
          <el-input v-model="createForm.excavation_year" placeholder="可选，如：2023" />
        </el-form-item>
        <el-form-item label="批次号">
          <el-input v-model="createForm.batch_no" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateGroup" :loading="groupStore.isLoading">创建</el-button>
      </template>
    </el-dialog>

    <!-- 导入图片对话框 -->
    <el-dialog v-model="showImportDialog" title="导入图片" width="600px" @close="resetUploadFiles">
      <el-upload
        ref="uploadRef"
        drag
        action="#"
        :auto-upload="false"
        :multiple="true"
        :limit="100"
        accept="image/*"
        :file-list="uploadFileList"
        @change="handleFileChange"
        @remove="handleFileRemove"
      >
        <template #default>
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            拖拽文件到此或<em>点击选择</em>
          </div>
        </template>
        <template #tip>
          <div class="el-upload__tip">
            支持 PNG/JPEG/BMP，单张最大 50MB，单次最多 100 张
          </div>
        </template>
      </el-upload>

      <!-- 已选文件列表 -->
      <div v-if="uploadFileList.length > 0" class="selected-files">
        <p>已选择 {{ uploadFileList.length }} 个文件</p>
      </div>

      <!-- 上传进度 -->
      <div v-if="uploadProgress.total > 0" class="upload-progress">
        <el-progress :percentage="uploadProgress.percent" :color="uploadProgressColor" />
        <p>{{ formatFileSize(uploadProgress.loaded) }} / {{ formatFileSize(uploadProgress.total) }}</p>
      </div>

      <template #footer>
        <el-button @click="showImportDialog = false" :disabled="uploading">取消</el-button>
        <el-button type="primary" @click="handleUpload" :loading="uploading" :disabled="uploadFileList.length === 0">
          开始上传
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { handleApiError } from '@/utils/errorHandler'
import { Plus, Picture, ArrowDown, UploadFilled, Check, Loading } from '@element-plus/icons-vue'
import { showError, ErrorLevel } from '@/utils/errorHandler'
import { useGroupStore } from '@/store/group'

const router = useRouter()

const API_BASE_URL = import.meta.env.VITE_BACKEND_BASE_URL || 'http://127.0.0.1:8000'

// Store
const groupStore = useGroupStore()

// 状态
const expandedGroupId = ref(null)
const expandedGroupName = ref('')
const showCreateDialog = ref(false)
const showImportDialog = ref(false)
const uploading = ref(false)
const currentGroupId = ref(null)
const currentPage = ref(1)
const selectedImages = ref([])

// 上传相关
const uploadRef = ref(null)
const uploadFileList = ref([])
const uploadProgress = ref({
  total: 0,
  loaded: 0,
  percent: 0
})

// 表单
const createFormRef = ref(null)
const createForm = ref({
  name: '',
  description: '',
  source_site: '',
  period: '',
  material: '',
  collection: '',
  excavation_year: '',
  batch_no: ''
})

// 表单验证规则
const createFormRules = {
  name: [
    { required: true, message: '请输入组名称', trigger: 'blur' }
  ]
}

// 方法
const openCreateDialog = () => {
  showCreateDialog.value = true
}

const resetCreateForm = () => {
  createForm.value = {
    name: '',
    description: '',
    source_site: '',
    period: '',
    material: '',
    collection: '',
    excavation_year: '',
    batch_no: ''
  }
  createFormRef.value?.clearValidate()
}

const handleCreateGroup = async () => {
  if (!createForm.value.name) {
    showError('请输入组名称', { level: ErrorLevel.WARNING })
    return
  }

  try {
    await groupStore.createGroup(createForm.value)
    ElMessage.success('图像组创建成功')
    showCreateDialog.value = false
    resetCreateForm()
  } catch (error) {
    handleApiError(error, '创建失败')
  }
}

const handleImportImages = (group) => {
  currentGroupId.value = group.id
  showImportDialog.value = true
}

const resetUploadFiles = () => {
  uploadFileList.value = []
  uploadProgress.value = { total: 0, loaded: 0, percent: 0 }
}

const handleFileChange = (file, fileList) => {
  uploadFileList.value = fileList
}

const handleFileRemove = (file, fileList) => {
  uploadFileList.value = fileList
}

const handleUpload = async () => {
  if (!currentGroupId.value || uploadFileList.value.length === 0) return

  uploading.value = true
  uploadProgress.value = { total: 0, loaded: 0, percent: 0 }

  try {
    const files = uploadFileList.value.map(f => f.raw)
    const totalSize = files.reduce((sum, f) => sum + f.size, 0)
    uploadProgress.value.total = totalSize

    await groupStore.uploadImages(
      currentGroupId.value,
      files,
      (progress) => {
        uploadProgress.value.loaded = progress.loaded
        uploadProgress.value.percent = progress.percent
      }
    )

    ElMessage.success(`成功上传 ${uploadFileList.value.length} 张图片`)
    showImportDialog.value = false
    resetUploadFiles()

    // 刷新组列表
    await groupStore.fetchGroups()

    // 刷新当前组详情（确保 total_images 更新）
    await groupStore.fetchGroupDetail(currentGroupId.value)

    // 如果当前展开的是这个组，刷新图片列表
    if (expandedGroupId.value === currentGroupId.value) {
      await groupStore.fetchImages(currentGroupId.value, currentPage.value)
    }
  } catch (error) {
    handleApiError(error, '上传失败')
  } finally {
    uploading.value = false
  }
}

const handlePreprocess = async (group) => {
  try {
    await ElMessageBox.confirm(
      `确定要对图像组"${group.name}"进行预处理吗？`,
      '预处理确认',
      { type: 'info' }
    )
    await groupStore.preprocess(group.id, {})
    ElMessage.success('预处理任务已提交')
    // 刷新组状态
    await groupStore.fetchGroups()
  } catch (error) {
    if (error !== 'cancel') {
      handleApiError(error, '预处理失败')
    }
  }
}

const handleSegmentSlips = (group) => {
  router.push({ path: '/batch-segmentation', query: { groupId: group.id } })
}

const handleDelete = async (group) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除图像组"${group.name}"及其所有数据吗？此操作无法撤销。`,
      '确认删除',
      { type: 'warning' }
    )
    await groupStore.deleteGroup(group.id)
    ElMessage.success('删除成功')
    // 如果删除的是展开的组，关闭展开
    if (expandedGroupId.value === group.id) {
      expandedGroupId.value = null
      expandedGroupName.value = ''
    }
  } catch (error) {
    if (error !== 'cancel') {
      handleApiError(error, '删除失败')
    }
  }
}

const toggleGroupExpand = async (group) => {
  if (expandedGroupId.value === group.id) {
    expandedGroupId.value = null
    expandedGroupName.value = ''
    selectedImages.value = []
  } else {
    expandedGroupId.value = group.id
    expandedGroupName.value = group.name
    currentPage.value = 1
    selectedImages.value = []
    await groupStore.fetchImages(group.id, 1)
  }
}

const closeExpandedGroup = () => {
  expandedGroupId.value = null
  expandedGroupName.value = ''
  selectedImages.value = []
}

const handlePageChange = async (page) => {
  currentPage.value = page
  await groupStore.fetchImages(expandedGroupId.value, page)
}

const toggleImageSelection = (imageId) => {
  const index = selectedImages.value.indexOf(imageId)
  if (index === -1) {
    selectedImages.value.push(imageId)
  } else {
    selectedImages.value.splice(index, 1)
  }
}

const handleBatchDeleteImages = async () => {
  if (selectedImages.value.length === 0) return

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedImages.value.length} 张图片吗？`,
      '确认删除',
      { type: 'warning' }
    )

    const groupId = expandedGroupId.value
    for (const imageId of selectedImages.value) {
      await groupStore.deleteImage(groupId, imageId)
    }

    ElMessage.success(`已删除 ${selectedImages.value.length} 张图片`)
    selectedImages.value = []

    // 刷新图片列表
    await groupStore.fetchImages(groupId, currentPage.value)
    // 刷新组列表和组详情（确保 total_images 更新）
    await groupStore.fetchGroups()
    await groupStore.fetchGroupDetail(groupId)
  } catch (error) {
    if (error !== 'cancel') {
      handleApiError(error, '删除失败')
    }
  }
}

const getProgressPercentage = (group) => {
  const total = group.total_images || 0
  const processed = group.processed_images || 0
  return total > 0 ? Math.round((processed / total) * 100) : 0
}

const getStatusType = (status) => {
  const map = {
    'created': 'info',
    'preprocessing': 'warning',
    'segmenting': 'warning',
    'completed': 'success',
    'exported': 'success'
  }
  return map[status] || 'info'
}

const getStatusLabel = (status) => {
  const map = {
    'created': '已创建',
    'preprocessing': '预处理中',
    'segmenting': '切割中',
    'completed': '已完成',
    'exported': '已导出'
  }
  return map[status] || status
}

const getProgressColor = (percentage) => {
  if (percentage < 50) return '#E6A23C'
  if (percentage < 100) return '#409EFF'
  return '#67C23A'
}

const uploadProgressColor = (percentage) => {
  if (percentage < 50) return '#E6A23C'
  if (percentage < 100) return '#409EFF'
  return '#67C23A'
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

const handleImageError = (e) => {
  e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2Y1ZjVmNSIvPjx0ZXh0IHg9IjUwIiB5PSI1NSIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSI+5Zu+54mHPC90ZXh0Pjwvc3ZnPg=='
}

const getImagePlaceholder = () => {
  return 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2Y1ZjVmNSIvPjwvc3ZnPg=='
}

const getFullImageUrl = (url) => {
  if (!url) return getImagePlaceholder()
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }
  return `${API_BASE_URL}${url}`
}

// 初始化
onMounted(async () => {
  await groupStore.fetchGroups()
})
</script>

<style scoped lang="scss">
.image-group-page {
  padding: 20px;
  background: #F5F0E8;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  h1 {
    margin: 0;
    font-size: 24px;
    color: #333;
  }
}

.groups-container {
  background: white;
  border-radius: 8px;
  padding: 20px;
}

.groups-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.group-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s;
  position: relative;

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .group-thumbnail {
    width: 100%;
    height: 200px;
    background: #f5f5f5;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .thumbnail-placeholder {
      font-size: 48px;
      color: #ccc;
    }
  }

  .group-info {
    padding: 15px;

    h3 {
      margin: 0 0 8px 0;
      font-size: 16px;
      color: #333;
    }

    .description {
      margin: 0 0 10px 0;
      font-size: 12px;
      color: #999;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
      font-size: 12px;

      .count {
        color: #666;
      }
    }

    .actions {
      display: flex;
      gap: 5px;
      margin-top: 10px;

      button {
        flex: 1;
        font-size: 12px;
      }
    }
  }

  .expand-btn {
    position: absolute;
    top: 10px;
    right: 10px;
    cursor: pointer;
    background: rgba(255, 255, 255, 0.9);
    border-radius: 50%;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s;

    &:hover {
      background: white;
    }

    &.expanded {
      transform: rotate(180deg);
    }

    .el-icon {
      transition: transform 0.3s;
    }
  }
}

.expanded-group {
  margin-top: 20px;
  background: white;
  border-radius: 8px;
  padding: 20px;

  .group-images {
    h3 {
      margin-bottom: 15px;
      font-size: 16px;
      color: #333;
    }

    .images-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 15px;

      h3 {
        margin: 0;
      }
    }

    .images-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 15px;

      .images-count {
        color: #666;
        font-size: 14px;
      }
    }

    .images-loading,
    .images-empty {
      text-align: center;
      padding: 40px;
      color: #999;
    }

    .images-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
      gap: 15px;

      .image-item {
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        overflow: hidden;
        text-align: center;
        cursor: pointer;
        position: relative;
        transition: all 0.2s;

        &:hover {
          border-color: #409EFF;
        }

        &.selected {
          border-color: #409EFF;
          background: rgba(64, 158, 255, 0.1);
        }

        .image-checkbox {
          position: absolute;
          top: 5px;
          right: 5px;
          width: 20px;
          height: 20px;
          background: #409EFF;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          z-index: 1;
        }

        img {
          width: 100%;
          height: 120px;
          object-fit: cover;
        }

        .filename {
          margin: 8px 4px 0;
          font-size: 12px;
          color: #333;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .size {
          margin: 0 4px 8px;
          font-size: 11px;
          color: #999;
        }
      }
    }

    .images-pagination {
      margin-top: 20px;
      display: flex;
      justify-content: center;
    }
  }
}

.selected-files {
  margin-top: 15px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 14px;
  color: #666;
}

.upload-progress {
  margin-top: 20px;

  p {
    margin-top: 10px;
    text-align: center;
    color: #666;
  }
}
</style>
