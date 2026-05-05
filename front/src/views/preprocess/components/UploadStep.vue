<template>
  <section class="step-shell">
    <el-alert type="info" :closable="false" show-icon title="建议 5-10 张，最多 10 张" />

    <div class="upload-panel">
      <el-upload
        ref="uploadRef"
        drag
        action="#"
        :auto-upload="false"
        :multiple="true"
        :limit="10"
        :on-change="handleChange"
        :on-remove="handleRemovePending"
        :on-exceed="handleExceed"
        :show-file-list="false"
        accept="image/*"
      >
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="upload-copy">拖拽图片到这里，或点击选择</div>
      </el-upload>

      <div class="upload-actions">
        <el-button type="primary" :loading="uploading" :disabled="pendingFiles.length === 0" @click="submitUpload">
          上传到当前组
        </el-button>
        <el-progress v-if="uploading || uploadPercent > 0" :percentage="uploadPercent" />
      </div>
    </div>

    <div class="lists-grid">
      <section class="list-card">
        <h3>待上传</h3>
        <el-empty v-if="pendingFiles.length === 0" description="还没有选择图片" />
        <div v-else class="file-list">
          <div v-for="file in pendingFiles" :key="file.uid" class="file-row">
            <span>{{ file.name }}</span>
            <el-button text @click="removePending(file.uid)">移除</el-button>
          </div>
        </div>
      </section>

      <section class="list-card">
        <h3>已上传</h3>
        <el-empty v-if="images.length === 0" description="当前组还没有图片" />
        <div v-else class="image-list">
          <div v-for="image in images" :key="image.id" class="image-row">
            <div class="image-meta">
              <LazyProtectedImage
                :src="image.file_url"
                :title="image.filename"
                label="查看"
              />
              <span>{{ image.filename }}</span>
            </div>
            <el-button text type="danger" @click="removeImage(image.id)">删除</el-button>
          </div>
        </div>
      </section>
    </div>

    <div class="footer-actions">
      <el-button
        type="primary"
        size="large"
        :disabled="images.length < 1 || pendingFiles.length > 0 || uploading"
        @click="$emit('next')"
      >
        下一步：开始批量估角
      </el-button>
    </div>
  </section>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { usePreprocessStore } from '@/store/preprocess'
import LazyProtectedImage from './LazyProtectedImage.vue'

const props = defineProps({
  groupId: { type: String, required: true }
})

defineEmits(['next'])

const store = usePreprocessStore()
const uploadRef = ref(null)
const pendingFiles = ref([])
const uploading = ref(false)

const images = computed(() => store.images)
const uploadPercent = computed(() => store.uploadPercent)

const handleExceed = () => {
  ElMessage.error('最多选择 10 张图片')
}

const handleChange = (file, fileList) => {
  pendingFiles.value = fileList.slice(0, 10)
  if (fileList.length > 10) {
    ElMessage.error('已自动截断到前 10 张')
  }
}

const handleRemovePending = (file, fileList) => {
  pendingFiles.value = fileList
}

const removePending = (uid) => {
  pendingFiles.value = pendingFiles.value.filter((file) => file.uid !== uid)
}

const submitUpload = async () => {
  try {
    uploading.value = true
    store.uploadPercent = 0
    await store.uploadImages(props.groupId, pendingFiles.value.map((item) => item.raw))
    pendingFiles.value = []
    ElMessage.success('图片已上传')
  } catch (error) {
    ElMessage.error(error.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

const removeImage = async (imageId) => {
  try {
    await store.deleteImage(props.groupId, imageId)
    ElMessage.success('已删除')
  } catch (error) {
    ElMessage.error(error.message || '删除失败')
  }
}
</script>

<style scoped>
.step-shell {
  display: grid;
  gap: 18px;
}

.upload-panel,
.list-card {
  background: #fff;
  border: 1px solid #eadfcf;
  border-radius: 8px;
  padding: 20px;
}

.upload-icon {
  font-size: 28px;
  color: #3d2817;
}

.upload-copy {
  margin-top: 8px;
  color: #2c1810;
}

.upload-actions {
  margin-top: 16px;
  display: grid;
  gap: 12px;
}

.lists-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.file-list,
.image-list {
  display: grid;
  gap: 10px;
}

.file-row,
.image-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.image-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.image-meta span {
  color: #2c1810;
}

.footer-actions {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 900px) {
  .lists-grid {
    grid-template-columns: 1fr;
  }
}
</style>
