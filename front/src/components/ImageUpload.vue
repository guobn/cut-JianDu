<template>
  <div class="image-upload">
    <el-upload
      ref="uploadRef"
      class="upload-area"
      drag
      :auto-upload="false"
      :show-file-list="false"
      :on-change="handleFileChange"
      :before-upload="beforeUpload"
      accept="image/jpeg,image/png,image/tiff,image/bmp"
    >
      <div v-if="!imagePreview" class="upload-content">
        <el-icon class="upload-icon" :size="48">
          <Upload />
        </el-icon>
        <div class="upload-text">
          <div class="upload-text__main">拖拽图像到此处或点击上传</div>
          <div class="upload-text__sub">支持 JPG、PNG、TIFF、BMP 格式，最大 50MB</div>
        </div>
      </div>

      <div v-else class="preview-container">
        <img
          :src="imagePreview"
          class="preview-image"
          alt="预览"
          width="240"
          height="180"
          loading="lazy"
        />
        <div class="preview-overlay">
          <el-button type="primary" :icon="RefreshRight" @click.stop="handleReupload">
            重新上传
          </el-button>
        </div>
      </div>
    </el-upload>

    <!-- 简牍编号输入 -->
    <div v-if="selectedFile && !isUploading" class="slip-number-input">
      <el-form :model="formData" label-width="80px">
        <el-form-item label="简牍编号">
          <el-input
            v-model="formData.slipNumber"
            placeholder="例如：里耶秦简 001 号 (可选)"
            clearable
            maxlength="50"
          >
            <template #prefix>
              <el-icon><Document /></el-icon>
            </template>
          </el-input>
          <div class="form-item-tip">
            编号将用于切割结果的文件命名，支持中文和数字
          </div>
        </el-form-item>
      </el-form>
    </div>

    <div v-if="imageInfo" class="image-info">
      <div class="image-info__item">
        <span class="image-info__label">文件名：</span>
        <span class="image-info__value">{{ imageInfo.filename }}</span>
      </div>
      <div class="image-info__item">
        <span class="image-info__label">尺寸：</span>
        <span class="image-info__value">{{ imageInfo.width }} × {{ imageInfo.height }}</span>
      </div>
      <div class="image-info__item">
        <span class="image-info__label">格式：</span>
        <span class="image-info__value">{{ imageInfo.format }}</span>
      </div>
      <div class="image-info__item">
        <span class="image-info__label">大小：</span>
        <span class="image-info__value">{{ formatFileSize(imageInfo.file_size) }}</span>
      </div>
      <div v-if="imageInfo.slip_number" class="image-info__item">
        <span class="image-info__label">简牍编号：</span>
        <span class="image-info__value">{{ imageInfo.slip_number }}</span>
      </div>
    </div>

    <div v-if="isUploading" class="upload-progress">
      <el-progress :percentage="100" :indeterminate="true" />
      <div class="upload-progress__text">正在上传...</div>
    </div>

    <div v-if="selectedFile && !isUploading" class="upload-actions">
      <el-button type="primary" :icon="Upload" @click="handleUpload" :loading="isUploading">
        确认上传
      </el-button>
      <el-button @click="handleCancel">取消</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, RefreshRight, Document } from '@element-plus/icons-vue'
import { useImageProcessingStore } from '@/store/imageProcessing'
import { handleUploadError } from '@/utils/errorHandler'
import imageProcessingAPI from '@/api/imageProcessing'

const emit = defineEmits(['uploaded', 'error'])

const imageStore = useImageProcessingStore()

const uploadRef = ref(null)
const selectedFile = ref(null)
const imagePreview = ref(null)

// 分片上传配置
const CHUNK_SIZE = 5 * 1024 * 1024 // 5MB per chunk
const UPLOAD_THRESHOLD = 10 * 1024 * 1024 // 10MB threshold for chunked upload
const MAX_CONCURRENT_UPLOADS = 3 // 最多并发 3 个分片

// 表单数据
const formData = reactive({
  slipNumber: ''
})

const isUploading = computed(() => imageStore.isUploading)
const imageInfo = computed(() => imageStore.currentImage)

/**
 * 文件选择变化
 */
function handleFileChange(file) {
  selectedFile.value = file.raw

  // 生成预览
  const reader = new FileReader()
  reader.onload = (e) => {
    imagePreview.value = e.target.result
  }
  reader.readAsDataURL(file.raw)
}

/**
 * 上传前验证
 */
function beforeUpload(file) {
  // 验证文件类型
  const validTypes = ['image/jpeg', 'image/png', 'image/tiff', 'image/bmp']
  if (!validTypes.includes(file.type)) {
    ElMessage.error('不支持的图像格式，请上传 JPG、PNG、TIFF 或 BMP 格式的图像')
    return false
  }

  // 验证文件大小（50MB）
  const maxSize = 50 * 1024 * 1024
  if (file.size > maxSize) {
    ElMessage.error('文件大小超过限制，请上传小于 50MB 的图像')
    return false
  }

  return true
}

/**
 * 分片上传函数
 */
async function uploadChunks(file) {
  const uploadId = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE)

  ElMessage.info(`文件大于 10MB，将使用分片上传模式（共${totalChunks}个分片）`)

  const uploadedChunks = ref([])
  const failedChunks = ref([])

  /**
   * 上传单个分片
   */
  async function uploadSingleChunk(index) {
    const start = index * CHUNK_SIZE
    const end = Math.min(start + CHUNK_SIZE, file.size)
    const chunkBlob = file.slice(start, end)

    const chunkFormData = new FormData()
    chunkFormData.append('chunk', chunkBlob)
    chunkFormData.append('upload_id', uploadId)
    chunkFormData.append('chunk_index', index)
    chunkFormData.append('total_chunks', totalChunks)
    chunkFormData.append('filename', file.name)

    const token = imageStore.$state.user?.session?.access_token
      || localStorage.getItem('access_token')
      || sessionStorage.getItem('access_token')

    try {
      const response = await fetch(`${imageProcessingAPI.constructor.baseUrl || 'http://127.0.0.1:8000'}/api/images/upload-chunk`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: chunkFormData
      })

      if (!response.ok) {
        throw new Error(`分片上传失败：${response.status}`)
      }

      const result = await response.json()
      uploadedChunks.value.push(index)
      return result
    } catch (error) {
      failedChunks.value.push(index)
      throw error
    }
  }

  /**
   * 并发上传分片
   */
  async function uploadChunksConcurrently() {
    const queue = []
    for (let i = 0; i < totalChunks; i++) {
      queue.push(i)
    }

    const activeTasks = []
    const results = []

    while (queue.length > 0 || activeTasks.length > 0) {
      // 启动新任务直到达到并发限制
      while (activeTasks.length < MAX_CONCURRENT_UPLOADS && queue.length > 0) {
        const index = queue.shift()
        const task = uploadSingleChunk(index)
          .then(result => {
            results[index] = result
            const taskIndex = activeTasks.indexOf(task)
            if (taskIndex > -1) {
              activeTasks.splice(taskIndex, 1)
            }
          })
          .catch(err => {
            console.error(`分片 ${index} 上传失败:`, err)
            const taskIndex = activeTasks.indexOf(task)
            if (taskIndex > -1) {
              activeTasks.splice(taskIndex, 1)
            }
            throw err
          })
        activeTasks.push(task)
      }

      // 等待至少一个任务完成
      if (activeTasks.length > 0) {
        await Promise.race(activeTasks)
      }
    }

    return results
  }

  try {
    // 并发上传所有分片
    await uploadChunksConcurrently()

    ElMessage.success(`所有分片上传成功，正在合并...`)

    // 合并分片
    const mergeFormData = new FormData()
    mergeFormData.append('upload_id', uploadId)
    mergeFormData.append('filename', file.name)
    mergeFormData.append('total_chunks', totalChunks)
    if (formData.slipNumber) {
      mergeFormData.append('slip_number', formData.slipNumber)
    }

    const token = imageStore.$state.user?.session?.access_token
      || localStorage.getItem('access_token')
      || sessionStorage.getItem('access_token')

    const mergeResponse = await fetch(`${imageProcessingAPI.constructor.baseUrl || 'http://127.0.0.1:8000'}/api/images/merge-chunks`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: mergeFormData
    })

    if (!mergeResponse.ok) {
      const errorData = await mergeResponse.json()
      throw new Error(errorData.detail?.error_message || '合并失败')
    }

    const result = await mergeResponse.json()
    return result

  } catch (error) {
    // 取消上传，清理临时文件
    try {
      await fetch(`${imageProcessingAPI.constructor.baseUrl || 'http://127.0.0.1:8000'}/api/images/abort-upload/${uploadId}`, {
        method: 'DELETE',
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      })
    } catch (e) {
      console.error('清理临时文件失败:', e)
    }
    throw error
  }
}

/**
 * 执行上传
 */
async function handleUpload() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择图像文件')
    return
  }

  try {
    imageStore.isUploading = true

    // 检查文件大小决定是否使用分片上传
    if (selectedFile.value.size > UPLOAD_THRESHOLD) {
      // 使用分片上传
      const result = await uploadChunks(selectedFile.value)
      ElMessage.success('图像上传成功（分片模式）')

      // 更新 store
      imageStore.currentImage = result
      imageStore.imageUrl = imageProcessingAPI.getImageUrl(result.image_id)

      emit('uploaded', { ...result, file: selectedFile.value })
    } else {
      // 使用普通上传
      const result = await imageStore.uploadImage(selectedFile.value, formData.slipNumber)
      ElMessage.success('图像上传成功')
      emit('uploaded', { ...result, file: selectedFile.value })
    }
  } catch (error) {
    handleUploadError(error, selectedFile.value)
    emit('error', error)
  } finally {
    imageStore.isUploading = false
  }
}

/**
 * 取消上传
 */
function handleCancel() {
  selectedFile.value = null
  imagePreview.value = null
  formData.slipNumber = ''
  uploadRef.value?.clearFiles()
}

/**
 * 重新上传
 */
function handleReupload() {
  handleCancel()
}

/**
 * 格式化文件大小
 */
function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}
</script>

<style scoped>
.image-upload {
  width: 100%;
}

.upload-area {
  width: 100%;
}

.upload-area :deep(.el-upload) {
  width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
  width: 100%;
  height: 200px;
  border-radius: 12px;
  border: 2px dashed rgba(64, 158, 255, 0.3);
  background: rgba(64, 158, 255, 0.02);
  transition: all 0.3s;
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: #409EFF;
  background: rgba(64, 158, 255, 0.05);
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 20px;
}

.upload-icon {
  color: #409EFF;
  margin-bottom: 16px;
}

.upload-text__main {
  font-size: 14px;
  font-weight: 600;
  color: #1f2d3d;
  margin-bottom: 8px;
}

.upload-text__sub {
  font-size: 12px;
  color: rgba(31, 45, 61, 0.6);
}

.preview-container {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-image {
  width: 240px;
  height: 180px;
  object-fit: contain;
  border-radius: var(--radius-md);
}

.preview-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s;
}

.preview-container:hover .preview-overlay {
  opacity: 1;
}

.image-info {
  margin-top: 16px;
  padding: 12px;
  border-radius: 8px;
  background: rgba(31, 45, 61, 0.03);
  border: 1px solid rgba(31, 45, 61, 0.1);
}

.image-info__item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 6px;
}

.image-info__item:last-child {
  margin-bottom: 0;
}

.image-info__label {
  color: rgba(31, 45, 61, 0.6);
  font-weight: 600;
}

.image-info__value {
  color: #1f2d3d;
  font-weight: 700;
}

.upload-actions {
  margin-top: 16px;
  display: flex;
  gap: 10px;
}

.upload-actions .el-button {
  flex: 1;
}

.upload-progress {
  margin-top: 16px;
}

.upload-progress__text {
  text-align: center;
  font-size: 12px;
  color: rgba(31, 45, 61, 0.6);
  margin-top: 8px;
}

.slip-number-input {
  margin-top: 16px;
  padding: 12px;
  border-radius: 8px;
  background: rgba(64, 158, 255, 0.03);
  border: 1px solid rgba(64, 158, 255, 0.1);
}

.slip-number-input :deep(.el-form-item) {
  margin-bottom: 0;
}

.form-item-tip {
  font-size: 12px;
  color: rgba(31, 45, 61, 0.5);
  margin-top: 4px;
  line-height: 1.4;
}
</style>
