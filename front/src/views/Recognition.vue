<template>
  <div class="rec-page">
    <div class="rec-page__container">
      <section class="rec-page__header">
        <div class="rec-page__title">图像预处理工作台</div>
        <div class="rec-page__subtitle">旋转校正与尺寸归一化</div>
      </section>

      <section class="rec-page__section">
        <el-row :gutter="18" class="rec-workbench">
          <!-- 左侧工具栏（保留原有视觉风格） -->
          <el-col :xs="24" :lg="3">
            <div class="toolbox">
              <div class="toolbox__title">视图工具</div>
              <div class="toolbox__btns">
                <el-tooltip v-for="t in tools" :key="t.key" :content="t.label" placement="right">
                  <el-button
                    class="toolbox__btn"
                    :type="activeTool === t.key ? 'primary' : 'default'"
                    :plain="activeTool !== t.key"
                    circle
                    @click="handleToolClick(t.key)"
                    :aria-label="t.label"
                    :aria-pressed="activeTool === t.key"
                  >
                    <el-icon :size="16"><component :is="t.icon" /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>

              <div class="toolbox__hint">
                1. 从左侧上传或选择图像<br />
                2. 先进行旋转校正<br />
                3. 再执行尺寸归一化
              </div>
            </div>
          </el-col>

          <!-- 中间图像工作区 -->
          <el-col :xs="24" :lg="13">
            <el-card class="panel-card panel-card--workspace" shadow="never">
              <template #header>
                <div class="panel-card__title">图像工作区</div>
              </template>

              <div class="workspace">
                <div class="workspace__stage">
                  <template v-if="displayImageUrl">
                    <img class="workspace__img" :src="displayImageUrl" alt="预处理图像" />
                  </template>
                  <template v-else>
                    <div class="workspace__placeholder">
                      <div class="workspace__placeholder-text">请先在右侧上传或选择一张图像</div>
                    </div>
                  </template>
                </div>

                <div class="workspace__footer">
                  <div class="workspace__status">
                    当前工具：<span class="workspace__status-strong">{{ toolLabel }}</span>
                  </div>
                  <div class="workspace__status">
                    图像尺寸：<span class="workspace__status-strong">{{ imageSizeText }}</span>
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>

          <!-- 右侧预处理控制面板 -->
          <el-col :xs="24" :lg="8">
            <el-card class="panel-card" shadow="never">
              <template #header>
                <div class="panel-card__title">图像选择与预处理</div>
              </template>

              <div class="right-panel">
                <!-- 未选择图像时：上传 + 已上传列表（参考 Segmentation 页） -->
                <div v-if="!hasImage" class="control-section">
                  <div class="right-panel__label">上传图像</div>
                  <ImageUpload @uploaded="handleImageUploaded" />

                  <div v-if="uploadedImages.length > 0" class="uploaded-images">
                    <div class="uploaded-images__title">或选择已上传的图像</div>
                    <div class="uploaded-images__list">
                      <div
                        v-for="img in uploadedImages"
                        :key="img.image_id"
                        class="uploaded-image-item"
                        @click="handleSelectUploadedImage(img)"
                      >
                        <img
                          :src="getImageUrl(img.image_id)"
                          :alt="img.filename"
                          class="uploaded-image-item__thumb"
                        />
                        <div class="uploaded-image-item__info">
                          <div class="uploaded-image-item__name">{{ img.filename }}</div>
                          <div class="uploaded-image-item__size">
                            {{ img.width }} × {{ img.height }}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 已选择图像时：旋转校正 + 尺寸归一化 -->
                <template v-else>
                  <!-- 当前图像信息 -->
                  <div class="control-section">
                    <div class="right-panel__label">当前图像信息</div>
                    <el-descriptions :column="1" size="small" border>
                      <el-descriptions-item label="文件名">
                        {{ imageStore.currentImage?.filename || '-' }}
                      </el-descriptions-item>
                      <el-descriptions-item label="原始尺寸">
                        {{ baseImageSizeText }}
                      </el-descriptions-item>
                      <el-descriptions-item label="显示尺寸">
                        {{ imageSizeText }}
                      </el-descriptions-item>
                    </el-descriptions>
                  </div>

                  <el-divider />

                  <!-- 旋转校正 -->
                  <div class="control-section">
                    <div class="right-panel__label">旋转校正</div>
                    <el-form label-position="left" label-width="90px" size="small">
                      <!-- 快速检测模式选择 -->
                      <el-form-item label="检测模式">
                        <el-switch
                          v-model="useFastDetection"
                          active-text="快速"
                          inactive-text="异步"
                          :active-icon="Lightning"
                          size="small"
                          style="--el-switch-on-color: #67c23a"
                        />
                        <el-tooltip content="快速检测：同步返回结果，速度快；异步检测：使用任务队列" placement="top">
                          <el-icon style="margin-left: 4px; cursor: help;"><QuestionFilled /></el-icon>
                        </el-tooltip>
                      </el-form-item>

                      <el-form-item label="自动检测">
                        <el-button
                          type="primary"
                          :loading="isDetecting"
                          :disabled="isDetecting || isProcessing"
                          @click="handleDetectAngle"
                        >
                          {{ isDetecting ? '检测中...' : '检测倾斜角度' }}
                        </el-button>
                      </el-form-item>

                      <el-form-item label="检测结果" v-if="rotationDetection">
                        <div class="detect-result">
                          <div>角度：{{ rotationDetection.detected_angle.toFixed(2) }}°</div>
                          <div v-if="rotationDetection.confidence">
                            置信度：{{ (rotationDetection.confidence * 100).toFixed(1) }}%
                          </div>
                        </div>
                      </el-form-item>

                      <el-form-item label="手动角度">
                        <el-input-number
                          v-model="manualAngle"
                          :min="ROTATION_ENGINE_PARAMS.min_angle"
                          :max="ROTATION_ENGINE_PARAMS.max_angle"
                          :step="ROTATION_ENGINE_PARAMS.angle_step"
                          placeholder="默认自动"
                        />
                      </el-form-item>

                      <el-form-item label="自动裁剪">
                        <el-switch v-model="autoCrop" />
                      </el-form-item>
                    </el-form>

                    <el-button
                      type="success"
                      class="full-btn"
                      :loading="isProcessing"
                      :disabled="isProcessing"
                      @click="handleApplyRotation"
                    >
                      {{ isProcessing ? '旋转处理中...' : '执行旋转校正' }}
                    </el-button>
                  </div>

                  <el-divider />

                  <!-- 尺寸归一化 -->
                  <div class="control-section">
                    <div class="right-panel__label">尺寸归一化</div>
                    <el-form label-position="left" label-width="90px" size="small">
                      <el-form-item label="目标宽度">
                        <el-input-number
                          v-model="normalizeParams.target_width"
                          :min="NORMALIZATION_ENGINE_PARAMS.min_size"
                          :max="NORMALIZATION_ENGINE_PARAMS.max_size"
                          :step="NORMALIZATION_ENGINE_PARAMS.size_step"
                        />
                      </el-form-item>
                      <el-form-item label="目标高度">
                        <el-input-number
                          v-model="normalizeParams.target_height"
                          :min="NORMALIZATION_ENGINE_PARAMS.min_size"
                          :max="NORMALIZATION_ENGINE_PARAMS.max_size"
                          :step="NORMALIZATION_ENGINE_PARAMS.size_step"
                        />
                      </el-form-item>
                      <el-form-item label="保持比例">
                        <el-switch v-model="normalizeParams.keep_aspect_ratio" />
                      </el-form-item>
                      <el-form-item label="填充颜色">
                        <el-select v-model="normalizeParams.padding_color" style="width: 100%">
                          <el-option
                            v-for="color in NORMALIZATION_ENGINE_PARAMS.supported_padding_colors"
                            :key="color"
                            :label="color === 'white' ? '白色' : '黑色'"
                            :value="color"
                          />
                        </el-select>
                      </el-form-item>
                    </el-form>

                    <el-button
                      type="primary"
                      class="full-btn"
                      :loading="isProcessing"
                      :disabled="isProcessing"
                      @click="handleNormalize"
                    >
                      {{ isProcessing ? '归一化处理中...' : '执行尺寸归一化' }}
                    </el-button>
                  </div>

                  <!-- 处理结果摘要 -->
                  <div v-if="hasAnyResult" class="control-section">
                    <div class="right-panel__label">最新处理结果</div>
                    <el-descriptions :column="1" size="small" border>
                      <el-descriptions-item label="类型">
                        <span v-if="normalizationResult">尺寸归一化</span>
                        <span v-else-if="rotationResult">旋转校正</span>
                      </el-descriptions-item>
                      <el-descriptions-item label="输出尺寸" v-if="rotationResult || normalizationResult">
                        <template v-if="normalizationResult">
                          {{ normalizationResult.target_width }} ×
                          {{ normalizationResult.target_height }}
                        </template>
                        <template v-else-if="rotationResult">
                          {{ rotationResult.width }} × {{ rotationResult.height }}
                        </template>
                      </el-descriptions-item>
                      <el-descriptions-item label="处理耗时" v-if="lastProcessingTime">
                        {{ lastProcessingTime }} 秒
                      </el-descriptions-item>
                    </el-descriptions>
                  </div>
                </template>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Crop, Rank, RefreshRight, ZoomIn, ZoomOut, Lightning, QuestionFilled } from '@element-plus/icons-vue'
import { useImageProcessingStore } from '@/store/imageProcessing'
import ImageUpload from '@/components/ImageUpload.vue'
import imageProcessingAPI from '@/api/imageProcessing'
import { handleApiError } from '@/utils/errorHandler'
import {
  NORMALIZATION_ENGINE_PARAMS,
  ROTATION_ENGINE_PARAMS
} from '@/config/engineParams'

const imageStore = useImageProcessingStore()

const tools = [
  { key: 'view', label: '查看图像', icon: Crop },
  { key: 'move', label: '移动视图', icon: Rank },
  { key: 'zoomIn', label: '放大', icon: ZoomIn },
  { key: 'zoomOut', label: '缩小', icon: ZoomOut },
  { key: 'reset', label: '重置视图', icon: RefreshRight }
]

const activeTool = ref('view')

// 已上传图像列表（参考 Segmentation 页面）
const uploadedImages = ref([])

// 旋转与归一化状态
const rotationDetection = ref(null)
const rotationResult = ref(null)
const normalizationResult = ref(null)

const manualAngle = ref(null)
const autoCrop = ref(true)
// 快速检测模式
const useFastDetection = ref(false)

const normalizeParams = ref({
  target_width: NORMALIZATION_ENGINE_PARAMS.default_target_width,
  target_height: NORMALIZATION_ENGINE_PARAMS.default_target_height,
  keep_aspect_ratio: NORMALIZATION_ENGINE_PARAMS.default_keep_aspect_ratio,
  padding_color: NORMALIZATION_ENGINE_PARAMS.default_padding_color,
  interpolation: NORMALIZATION_ENGINE_PARAMS.default_interpolation
})

const hasImage = computed(() => imageStore.hasImage)
const isDetecting = computed(() => imageStore.isDetecting)
const isProcessing = computed(() => imageStore.isProcessing)

// 显示的图像优先级：归一化结果 > 旋转结果 > 原始图像
const displayImageUrl = computed(() => {
  if (normalizationResult.value?.output_path) {
    return getResultImageUrl(normalizationResult.value.output_path)
  }
  if (rotationResult.value?.output_path) {
    return getResultImageUrl(rotationResult.value.output_path)
  }
  return imageStore.imageUrl || ''
})

const baseImageSizeText = computed(() => {
  const img = imageStore.currentImage
  if (!img) return '-'
  return `${img.width} × ${img.height}`
})

const imageSizeText = computed(() => {
  if (normalizationResult.value) {
    return `${normalizationResult.value.target_width} × ${normalizationResult.value.target_height}`
  }
  if (rotationResult.value) {
    return `${rotationResult.value.width} × ${rotationResult.value.height}`
  }
  return baseImageSizeText.value
})

const hasAnyResult = computed(() => !!rotationResult.value || !!normalizationResult.value)

const lastProcessingTime = computed(() => {
  if (normalizationResult.value?.processing_time) {
    return normalizationResult.value.processing_time.toFixed(3)
  }
  if (rotationResult.value?.processing_time) {
    return rotationResult.value.processing_time.toFixed(3)
  }
  if (rotationDetection.value?.processing_time) {
    return rotationDetection.value.processing_time.toFixed(3)
  }
  return ''
})

onMounted(() => {
  loadUploadedImages()
})

function handleToolClick(key) {
  activeTool.value = key
}

async function loadUploadedImages() {
  try {
    const images = await imageProcessingAPI.listImages(10)
    uploadedImages.value = images
  } catch (error) {
    console.error('加载已上传图像列表失败:', error)
  }
}

function getImageUrl(imageId) {
  return imageProcessingAPI.getImageUrl(imageId)
}

// 结果图像 URL（与 Segmentation 中的用法保持一致）
function getResultImageUrl(path) {
  // 后端返回的是结果目录下的相对/绝对路径，这里简单拼接到后端服务地址
  return `http://127.0.0.1:8000/${path}`
}

function resetProcessState() {
  rotationDetection.value = null
  rotationResult.value = null
  normalizationResult.value = null
  manualAngle.value = null
}

function handleImageUploaded() {
  // ImageUpload 已经将 currentImage / imageUrl 写入到 store
  resetProcessState()
  loadUploadedImages()
}

async function handleSelectUploadedImage(img) {
  try {
    imageStore.currentImage = {
      image_id: img.image_id,
      filename: img.filename,
      width: img.width,
      height: img.height,
      format: img.format,
      file_size: img.file_size
    }
    imageStore.imageUrl = getImageUrl(img.image_id)
    resetProcessState()
    ElMessage.success('图像加载成功')
  } catch (error) {
    console.error('选择图像失败:', error)
    handleApiError(error, '选择图像失败')
  }
}

async function handleDetectAngle() {
  try {
    let result
    // 根据 useFastDetection 选择检测方式
    if (useFastDetection.value) {
      result = await imageStore.detectRotationAngleFast()
    } else {
      result = await imageStore.detectRotationAngle()
    }
    rotationDetection.value = result
    manualAngle.value = result.detected_angle || result.angle
    ElMessage.success(`角度检测完成${useFastDetection.value ? '（快速模式）' : ''}`)
  } catch (error) {
    handleApiError(error, '角度检测失败')
  }
}

async function handleApplyRotation() {
  try {
    const angle =
      manualAngle.value === null || manualAngle.value === '' ? null : Number(manualAngle.value)

    let result
    // 根据 useFastDetection 选择校正方式
    if (useFastDetection.value) {
      result = await imageStore.correctRotationFast(angle, autoCrop.value)
    } else {
      result = await imageStore.correctRotation(angle, autoCrop.value)
    }
    rotationResult.value = result
    normalizationResult.value = null
    ElMessage.success(`旋转校正完成${useFastDetection.value ? '（快速模式）' : ''}`)
  } catch (error) {
    handleApiError(error, '旋转校正失败')
  }
}

async function handleNormalize() {
  try {
    const result = await imageStore.normalizeSize(normalizeParams.value)
    normalizationResult.value = result
    ElMessage.success('尺寸归一化完成')
  } catch (error) {
    handleApiError(error, '尺寸归一化失败')
  }
}
</script>

<style scoped>
.rec-page {
  width: 100%;
}

.rec-page__container {
  max-width: 1180px;
  margin: 0 auto;
}

.rec-page__header {
  padding: 6px 2px 8px;
}

.rec-page__title {
  font-size: 22px;
  font-weight: 800;
  color: #1f2d3d;
  letter-spacing: 0.6px;
}

.rec-page__subtitle {
  margin-top: 6px;
  font-size: 12px;
  color: rgba(31, 45, 61, 0.62);
  letter-spacing: 0.35px;
}

.rec-page__section {
  margin-top: 18px;
}

.rec-workbench {
  align-items: stretch;
  min-height: 520px;
}

.panel-card {
  height: 100%;
  border-radius: 12px;
  border: 1px solid rgba(31, 45, 61, 0.10);
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 10px 20px rgba(17, 24, 39, 0.05);
}

.panel-card__title {
  font-size: 14px;
  font-weight: 800;
  color: #1f2d3d;
}

.panel-card--workspace {
  background: rgba(255, 255, 255, 0.96);
}

.toolbox {
  height: 100%;
  border-radius: 12px;
  border: 1px solid rgba(31, 45, 61, 0.10);
  background: rgba(31, 45, 61, 0.03);
  box-shadow: 0 10px 20px rgba(17, 24, 39, 0.04);
  padding: 12px 10px;
}

.toolbox__title {
  font-size: 12px;
  font-weight: 900;
  color: rgba(31, 45, 61, 0.70);
  margin-bottom: 10px;
}

.toolbox__btns {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  justify-items: center;
}

.toolbox__btn {
  width: 38px;
  height: 38px;
  border-radius: 12px;
}

.toolbox__hint {
  margin-top: 14px;
  font-size: 11px;
  color: rgba(31, 45, 61, 0.55);
  line-height: 1.6;
}

.workspace {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.workspace__stage {
  position: relative;
  flex: 1;
  min-height: 460px;
  border-radius: 12px;
  background: #111827;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.workspace__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.92;
}

.bbox {
  position: absolute;
  border: 2px dashed rgba(255, 255, 255, 0.85);
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.12s ease, border-color 0.12s ease;
}

.bbox:hover {
  background: rgba(59, 130, 246, 0.12);
  border-color: rgba(59, 130, 246, 0.9);
}

.bbox.is-active {
  background: rgba(34, 197, 94, 0.12);
  border-color: rgba(34, 197, 94, 0.95);
}

.workspace__footer {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(31, 45, 61, 0.10);
  background: rgba(31, 45, 61, 0.03);
}

.workspace__status {
  font-size: 12px;
  color: rgba(31, 45, 61, 0.70);
}

.workspace__status-strong {
  font-weight: 900;
  color: #1f2d3d;
}

.right-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.right-panel__table {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(31, 45, 61, 0.08);
}

:deep(.el-table th.el-table__cell) {
  background: rgba(31, 45, 61, 0.03);
}

:deep(.el-table .is-selected) {
  --el-table-tr-bg-color: rgba(64, 158, 255, 0.10);
}

.conf {
  display: flex;
  align-items: center;
  gap: 8px;
}

.conf__bar {
  width: 52px;
  height: 6px;
  border-radius: 999px;
  background: rgba(31, 45, 61, 0.12);
  overflow: hidden;
}

.conf__fill {
  height: 100%;
  background: rgba(34, 197, 94, 0.85);
}

.conf__text {
  font-size: 11px;
  color: rgba(31, 45, 61, 0.70);
}

.op-btn {
  padding: 0;
}

.right-panel__divider {
  height: 1px;
  background: rgba(31, 45, 61, 0.08);
  margin: 14px 0;
}

.right-panel__editor {
  margin-top: auto;
}

.right-panel__label {
  font-size: 12px;
  font-weight: 900;
  color: rgba(31, 45, 61, 0.70);
  margin-bottom: 10px;
}

.right-panel__actions {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.control-section {
  margin-bottom: 18px;
}

.full-btn {
  width: 100%;
  margin-top: 4px;
}

.detect-result {
  font-size: 12px;
  color: rgba(31, 45, 61, 0.8);
  line-height: 1.6;
}

.workspace__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
}

.workspace__placeholder-text {
  max-width: 220px;
  text-align: center;
}

.workspace__img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.uploaded-images {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid rgba(31, 45, 61, 0.1);
}

.uploaded-images__title {
  font-size: 12px;
  font-weight: 700;
  color: rgba(31, 45, 61, 0.7);
  margin-bottom: 12px;
}

.uploaded-images__list {
  max-height: 260px;
  overflow-y: auto;
}

.uploaded-image-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid rgba(31, 45, 61, 0.1);
  background: rgba(255, 255, 255, 0.5);
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.3s;
}

.uploaded-image-item:hover {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.05);
  transform: translateX(4px);
}

.uploaded-image-item__thumb {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 6px;
  background: #f5f5f5;
  flex-shrink: 0;
}

.uploaded-image-item__info {
  flex: 1;
  min-width: 0;
}

.uploaded-image-item__name {
  font-size: 13px;
  font-weight: 600;
  color: #1f2d3d;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.uploaded-image-item__size {
  font-size: 11px;
  color: rgba(31, 45, 61, 0.6);
}

/* Responsive adjustments */
@media (max-width: 992px) {
  .rec-page__container {
    max-width: 100%;
  }

  .rec-workbench {
    min-height: 480px;
  }

  .workspace__stage {
    min-height: 360px;
  }
}

@media (max-width: 768px) {
  .rec-page__header {
    padding: 4px 2px 6px;
  }

  .rec-page__title {
    font-size: 18px;
  }

  .rec-page__subtitle {
    font-size: 11px;
  }

  .rec-workbench {
    min-height: auto;
  }

  .toolbox {
    padding: 10px 8px;
  }

  .toolbox__btn {
    width: 34px;
    height: 34px;
  }

  .workspace__stage {
    min-height: 300px;
    height: 400px;
  }

  .panel-card__title {
    font-size: 13px;
  }
}

@media (max-width: 576px) {
  .workspace__stage {
    height: 350px;
  }

  .uploaded-images__list {
    max-height: 180px;
  }

  .uploaded-image-item__thumb {
    width: 50px;
    height: 50px;
  }
}
</style>
