<template>
  <div class="seg-page">
    <div class="seg-page__container">
      <section class="seg-page__header">
        <div class="seg-page__title">图像切割工作台</div>
        <div class="seg-page__subtitle">单支简牍切割与单字切割</div>
      </section>

      <section class="seg-page__section">
        <el-row :gutter="18" class="seg-workbench">
          <!-- 左侧工具栏 -->
          <el-col :xs="24" :lg="2">
            <div class="toolbox">
              <div class="toolbox__title">工具</div>
              <div class="toolbox__btns">
                <el-tooltip v-for="t in tools" :key="t.key" :content="t.label" placement="right">
                  <el-button
                    class="toolbox__btn"
                    :type="activeTool === t.key ? 'primary' : 'default'"
                    :plain="activeTool !== t.key"
                    :disabled="!hasImage && t.key !== 'select'"
                    circle
                    @click="handleToolClick(t.key)"
                    :aria-label="t.label"
                    :aria-pressed="activeTool === t.key"
                  >
                    <el-icon :size="16"><component :is="t.icon" /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </div>
          </el-col>

          <!-- 中间工作区 -->
          <el-col :xs="24" :lg="14">
            <el-card class="panel-card panel-card--workspace" shadow="never">
              <template #header>
                <div class="workspace-header">
                  <div class="panel-card__title">图像工作区</div>
                  <div class="workspace-header__tools">
                    <el-button-group size="small">
                      <el-button @click="handleZoom(0.5)" :disabled="!hasImage">50%</el-button>
                      <el-button @click="handleZoom(0.75)" :disabled="!hasImage">75%</el-button>
                      <el-button type="primary" @click="handleZoom(1)" :disabled="!hasImage">100%</el-button>
                      <el-button @click="handleFitCanvas" :disabled="!hasImage">适应</el-button>
                    </el-button-group>
                  </div>
                </div>
              </template>

              <div class="workspace">
                <div class="workspace__stage" ref="canvasContainer">
                  <canvas ref="fabricCanvas"></canvas>
                  <div v-if="!hasImage" class="workspace__placeholder">
                    <el-icon :size="48" color="#ccc"><Picture /></el-icon>
                    <div class="workspace__placeholder-text">请上传图像开始处理</div>
                  </div>
                </div>

                <div class="workspace__footer">
                  <div class="workspace__status">
                    当前工具：<span class="workspace__status-strong">{{ toolLabel }}</span>
                  </div>
                  <div class="workspace__status">
                    检测框数量：<span class="workspace__status-strong">{{ detectionCount }}</span>
                  </div>
                  <div class="workspace__status">
                    图像尺寸：<span class="workspace__status-strong">{{ imageSizeText }}</span>
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>

          <!-- 右侧控制面板 -->
          <el-col :xs="24" :lg="8">
            <el-card class="panel-card" shadow="never">
              <template #header>
                <div class="panel-card__title">切割设置</div>
              </template>

              <div class="control-panel">
                <!-- 图像上传 -->
                <div v-if="!hasImage" class="control-panel__section">
                  <div class="control-panel__label">图像来源</div>
                  <el-radio-group v-model="imageSource" class="mode-radio">
                    <el-radio value="raw">原图</el-radio>
                    <el-radio value="slip">单支图片</el-radio>
                  </el-radio-group>

                  <el-divider />

                  <template v-if="imageSource === 'raw'">
                    <div class="control-panel__label">上传图像</div>
                    <ImageUpload @uploaded="handleImageUploaded" />

                    <!-- 已上传图像列表 -->
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
                            <div class="uploaded-image-item__size">{{ img.width }} × {{ img.height }}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </template>

                  <template v-else>
                    <div v-if="slipSegments.length > 0" class="uploaded-images">
                      <div class="uploaded-images__title">选择可切割的单支图片</div>
                      <div class="uploaded-images__list">
                        <div
                          v-for="seg in slipSegments"
                          :key="seg.segment_id"
                          class="uploaded-image-item"
                          @click="handleSelectSlipSegment(seg)"
                        >
                          <img
                            :src="getSegmentUrl(seg)"
                            :alt="seg.storage_path"
                            class="uploaded-image-item__thumb"
                          />
                          <div class="uploaded-image-item__info">
                            <div class="uploaded-image-item__name">{{ getSegmentName(seg) }}</div>
                            <div class="uploaded-image-item__size">{{ seg.width }} × {{ seg.height }}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <el-empty v-else description="暂无单支图片，请先对原图执行单支切割" :image-size="80" />
                  </template>
                </div>

                <template v-else>
                  <!-- 模式选择 -->
                  <div class="control-panel__section">
                    <div class="control-panel__label">工作模式</div>
                    <el-radio-group v-model="processingMode" class="mode-radio">
                      <el-radio value="manual">手动模式</el-radio>
                      <el-radio value="model">模型调整模式</el-radio>
                    </el-radio-group>
                    <div class="control-panel__hint" v-if="processingMode === 'manual'">
                      手动模式：点击“添加框”手动绘制并调整边界框，然后执行切割。
                    </div>
                    <div class="control-panel__hint" v-else>
                      模型调整模式：自动检测后可微调边界框，再执行切割。
                    </div>
                  </div>

                  <el-divider />

                  <!-- 模型调整模式下显示检测参数 -->
                  <template v-if="processingMode === 'model'">
                    <!-- 检测引擎选择（根据切割模式区分显示不同引擎） -->
                    <div class="control-panel__section">
                      <ModelSelector
                        v-model="selectedEngine"
                        :show-params="true"
                        :show-description="true"
                        :mode="segmentationMode === 'single-slip' ? 'slip' : 'character'"
                        @change="handleEngineChange"
                      />
                    </div>

                    <el-divider />

                    <!-- 切割模式选择 -->
                    <div class="control-panel__section">
                      <div class="control-panel__label">切割模式</div>
                      <el-radio-group v-model="segmentationMode" class="mode-radio">
                        <el-radio value="single-slip" :disabled="imageSource === 'slip'">单支切割</el-radio>
                        <el-radio value="single-character" :disabled="imageSource === 'raw'">单字切割</el-radio>
                      </el-radio-group>
                    </div>

                    <el-divider />

                    <!-- 快速检测模式选择 -->
                    <div class="control-panel__section">
                      <div class="control-panel__label">
                        检测模式
                        <el-tooltip content="快速检测：同步返回结果，速度快；异步检测：使用任务队列，适合批量处理" placement="top">
                          <el-icon style="margin-left: 4px; cursor: help;"><QuestionFilled /></el-icon>
                        </el-tooltip>
                      </div>
                      <el-switch
                        v-model="useFastDetection"
                        active-text="快速检测"
                        inactive-text="异步检测"
                        :active-icon="Lightning"
                        style="--el-switch-on-color: #67c23a"
                      />
                      <div class="control-panel__hint" style="margin-top: 8px;">
                        {{ useFastDetection ? '快速检测：直连后端，立即返回结果（推荐用于开发测试）' : '异步检测：使用 Celery 任务队列（推荐用于生产环境）' }}
                      </div>
                    </div>

                    <el-divider />

                    <!-- 单支切割：不展示参数，直接识别 -->
                    <div v-if="segmentationMode === 'single-slip'" class="control-panel__section">
                      <div class="control-panel__hint control-panel__hint--slip">
                        单支切割使用模型自动识别，点击「自动检测」即可，无需调参。
                      </div>
                    </div>

                    <!-- 单字切割参数 -->
                    <div v-else class="control-panel__section">
                      <div class="control-panel__label">检测参数</div>
                      
                      <el-form label-position="left" label-width="100px" size="small">
                        <el-form-item label="最小宽度">
                          <el-input-number v-model="charParams.min_width" :min="10" :max="200" />
                        </el-form-item>

                        <el-form-item label="最小高度">
                          <el-input-number v-model="charParams.min_height" :min="10" :max="200" />
                        </el-form-item>

                        <el-form-item label="最大宽度">
                          <el-input-number v-model="charParams.max_width" :min="50" :max="500" />
                        </el-form-item>

                        <el-form-item label="最大高度">
                          <el-input-number v-model="charParams.max_height" :min="50" :max="500" />
                        </el-form-item>

                        <el-form-item label="背景类型">
                          <el-select v-model="charParams.background_type" style="width: 100%">
                            <el-option label="白底" value="white" />
                            <el-option label="黑底" value="black" />
                          </el-select>
                        </el-form-item>
                      </el-form>
                    </div>

                    <el-divider />
                  </template>

                  <!-- 检测结果列表 -->
                  <div class="control-panel__section">
                    <div class="control-panel__label">
                      检测结果
                      <span v-if="detectionCount > 0" class="control-panel__count">({{ detectionCount }})</span>
                    </div>
                    
                    <div v-if="detectionCount > 0" class="detection-list">
                      <div
                        v-for="(det, index) in detectionResults?.detections"
                        :key="det.id"
                        class="detection-item"
                      >
                        <div class="detection-item__order">{{ index + 1 }}</div>
                        <div class="detection-item__info">
                          <div class="detection-item__size">
                            {{ det.width }} × {{ det.height }}
                          </div>
                          <div v-if="det.confidence" class="detection-item__confidence">
                            置信度: {{ (det.confidence * 100).toFixed(1) }}%
                          </div>
                        </div>
                        <el-button
                          type="danger"
                          :icon="Delete"
                          size="small"
                          circle
                          @click="handleDeleteBox(det.id)"
                        />
                      </div>
                    </div>
                    <el-empty v-else description="暂无检测结果" :image-size="80" />
                  </div>

                  <el-divider />

                  <!-- 操作按钮 -->
                  <div class="control-panel__actions">
                    <el-button
                      v-if="processingMode === 'model'"
                      type="primary"
                      :icon="Search"
                      :loading="isDetecting"
                      :disabled="isDetecting || isProcessing"
                      @click="handleDetect"
                      style="width: 100%"
                    >
                      {{ isDetecting ? (taskProgress ? `检测中... ${taskProgress}%` : '检测中...') : '自动检测' }}
                    </el-button>
                    <el-button
                      v-if="processingMode === 'manual'"
                      type="primary"
                      :icon="Plus"
                      :disabled="isProcessing"
                      @click="handleAddBox"
                      style="width: 100%"
                    >
                      添加框
                    </el-button>
                    <el-button
                      :icon="RefreshRight"
                      :disabled="detectionCount === 0 || isDetecting || isProcessing"
                      @click="handleClearDetections"
                      style="width: 100%"
                    >
                      清空检测框
                    </el-button>
                    <el-button
                      type="success"
                      :icon="Scissor"
                      :loading="isProcessing"
                      :disabled="detectionCount === 0 || isDetecting || isProcessing"
                      @click="handleCut"
                      style="width: 100%"
                    >
                      {{ isProcessing ? '切割中...' : '执行切割' }}
                    </el-button>
                    <el-button
                      :icon="Download"
                      :disabled="!segmentationResults"
                      @click="handleDownload"
                      style="width: 100%"
                    >
                      下载结果
                    </el-button>
                    <el-button
                      :icon="RefreshLeft"
                      @click="handleReset"
                      style="width: 100%"
                    >
                      重新开始
                    </el-button>
                  </div>
                </template>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </section>

      <!-- 切割结果对话框 -->
      <el-dialog
        v-model="showResultsDialog"
        title="切割结果"
        width="80%"
        :close-on-click-modal="false"
      >
        <div v-if="segmentationResults" class="results-grid">
          <div
            v-for="(result, index) in segmentationResults.results"
            :key="result.id"
            class="result-item"
          >
            <div class="result-item__order">{{ index + 1 }}</div>
            <img
              :src="getResultImageUrl(result)"
              :alt="`切割结果 ${index + 1}`"
              class="result-item__image"
            />
            <div class="result-item__info">
              <div>{{ result.width }} × {{ result.height }}</div>
              <div class="result-item__filename">{{ result.filename }}</div>
              <div v-if="result.segment_id" class="result-item__actions">
                <el-button
                  type="primary"
                  size="small"
                  :icon="EditPen"
                  @click.stop="handleViewMetadata(result.segment_id)"
                >
                  查看元数据
                </el-button>
              </div>
            </div>
          </div>
        </div>
        <template #footer>
          <el-button @click="showResultsDialog = false">关闭</el-button>
          <el-button type="primary" :icon="Download" @click="handleDownloadAll">
            下载全部
          </el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { handleApiError } from '@/utils/errorHandler'
import {
  Crop,
  Delete,
  Download,
  Plus,
  EditPen,
  Picture,
  Pointer,
  Rank,
  RefreshRight,
  RefreshLeft,
  Scissor,
  Search,
  ZoomIn,
  ZoomOut,
  Lightning,
  QuestionFilled
} from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { useImageProcessingStore } from '@/store/imageProcessing'
import { CanvasHelper } from '@/utils/canvasHelper'
import ImageUpload from '@/components/ImageUpload.vue'
import ModelSelector from '@/components/ModelSelector.vue'
import imageProcessingAPI from '@/api/imageProcessing'
import { DEFAULT_DETECT_ENGINE } from '@/config/engineParams'

const imageStore = useImageProcessingStore()
const router = useRouter()

// Refs
const canvasContainer = ref(null)
const fabricCanvas = ref(null)
let canvasHelper = null

// 已上传的图像列表
const uploadedImages = ref([])

// 可选单支图片（来自 Supabase segments 表）
const slipSegments = ref([])
// 当前选择用于“单字切割”的单支 segment（用于构建 parent_segment_id）
const currentSlipSegment = ref(null)

// 图像来源：raw 原图；slip 单支图片
const imageSource = ref('raw')

// 工具栏配置
const tools = [
  { key: 'select', label: '选择工具', icon: Pointer },
  { key: 'delete', label: '删除', icon: Delete },
  { key: 'zoomIn', label: '放大', icon: ZoomIn },
  { key: 'zoomOut', label: '缩小', icon: ZoomOut }
]

const activeTool = ref('select')
// 模式：manual 手动添加框；model 模型自动检测（原有）
const processingMode = ref('model')
const segmentationMode = ref('single-slip')
const showResultsDialog = ref(false)
// 当前选择的检测引擎
const selectedEngine = ref(DEFAULT_DETECT_ENGINE)
// 快速检测模式：true 使用同步快速检测，false 使用异步 Celery 检测
const useFastDetection = ref(false)

// 单支切割参数
const slipParams = ref({
  min_width: 20,  // 降低从 50 到 20，避免过滤掉典型单支（宽度 20-50px）
  min_height: 40,  // 降低从 200 到 40，避免过滤掉较短单支
  aspect_ratio_min: 0.05,
  aspect_ratio_max: 0.6,  // 放宽从 0.2 到 0.6，适应不同形状的单支
  background_type: 'white'
})

watch(imageSource, (val) => {
  if (val === 'slip') {
    segmentationMode.value = 'single-character'
  } else {
    segmentationMode.value = 'single-slip'
  }
})

// 当切割模式切换时，重置引擎选择为默认值（因为单支和单字的引擎选项不同）
watch(segmentationMode, (newMode) => {
  if (newMode === 'single-slip') {
    selectedEngine.value = 'yolov8'
  } else {
    selectedEngine.value = 'yolov8'
  }
})

// 单字切割参数
const charParams = ref({
  min_width: 20,
  min_height: 20,
  max_width: 150,
  max_height: 150,
  background_type: 'white'
})

// 计算属性
const toolLabel = computed(() => tools.find((t) => t.key === activeTool.value)?.label ?? '-')
const hasImage = computed(() => imageStore.hasImage)
const isDetecting = computed(() => imageStore.isDetecting)
const isProcessing = computed(() => imageStore.isProcessing)
const detectionResults = computed(() => imageStore.detectionResults)
const segmentationResults = computed(() => imageStore.segmentationResults)
const detectionCount = computed(() => imageStore.detectionCount)
const taskProgress = computed(() => imageStore.taskProgress)

const imageSizeText = computed(() => {
  if (!imageStore.currentImage) return '-'
  return `${imageStore.currentImage.width} × ${imageStore.currentImage.height}`
})

// 生命周期
onMounted(() => {
  console.log('=== Segmentation 组件已挂载 ===')
  
  // 等待 DOM 完全渲染后再初始化
  nextTick(() => {
    console.log('nextTick: 开始初始化 Canvas')
    
    // 再延迟一点确保容器尺寸已确定
    setTimeout(() => {
      initCanvas()
      loadUploadedImages()
      loadSlipSegments()
    }, 300)
  })
})

onBeforeUnmount(() => {
  if (canvasHelper) {
    canvasHelper.dispose()
  }
})

// 方法

/**
 * 初始化 Canvas
 */
function initCanvas() {
  const container = canvasContainer.value
  if (!container || !fabricCanvas.value) {
    console.error('初始化失败：找不到 DOM 元素')
    return
  }

  // 关键：从容器获取真实的整数尺寸
  const width = Math.floor(container.clientWidth)
  const height = Math.floor(container.clientHeight)

  // 如果尺寸太小，给一个保底值，防止计算出错
  const finalWidth = width > 0 ? width : 800
  const finalHeight = height > 0 ? height : 600

  console.log(`正在初始化画布尺寸: ${finalWidth}x${finalHeight}`)

  // 销毁旧实例防止内存泄漏
  if (canvasHelper) {
    canvasHelper.dispose()
  }

  canvasHelper = new CanvasHelper(fabricCanvas.value, {
    width: finalWidth,
    height: finalHeight,
    backgroundColor: '#f5f5f5'
  })

  canvasHelper.onBoxesChanged = (boxes) => {
    if (!boxes) return
    if (imageStore.detectionResults) {
      imageStore.updateDetectionResults(boxes)
    } else {
      imageStore.detectionResults = {
        detection_id: `manual_${Date.now()}`,
        image_id: imageStore.currentImage?.image_id,
        mode: 'manual',
        detections: boxes,
        parameters: {},
        total_count: boxes.length,
        processing_time: 0,
        created_at: new Date()
      }
    }
  }

  // 挂载到全局方便 F12 调试
  window.canvasHelper = canvasHelper
}

/**
 * 图像上传成功
 */
async function handleImageUploaded(imageInfo) {
  try {
    // A. 确保页面 DOM 已根据 Vue 数据更新
    await nextTick()

    // B. 如果还没有初始化 Helper，立即初始化
    if (!canvasHelper) {
      initCanvas()
    }

    // C. 优先使用 Blob URL 加载（本地预览最快且避开 CORS）
    let loadUrl = ''
    if (imageInfo.file) {
      loadUrl = URL.createObjectURL(imageInfo.file)
    } else if (imageStore.imageUrl) {
      loadUrl = imageStore.imageUrl
    }

    if (!loadUrl) {
      throw new Error('无法获取图像 URL')
    }

    // D. 执行加载
    console.log('开始渲染图片:', loadUrl)
    await canvasHelper.loadImage(loadUrl)

    // E. 同步 Store 状态（如果需要）
    ElMessage.success('图片已成功渲染至工作区')
  } catch (error) {
    console.error('渲染流程中断:', error)
    handleApiError(error, '图片加载失败')
  }
}

function getSegmentUrl(seg) {
  const timestamp = new Date().getTime()
  return `${seg.public_url}?t=${timestamp}`
}

function getSegmentName(seg) {
  const p = seg.storage_path || ''
  const parts = p.split('/')
  return parts[parts.length - 1] || seg.segment_id
}

async function handleSelectSlipSegment(seg) {
  try {
    segmentationMode.value = 'single-character'
    currentSlipSegment.value = seg
    const url = getSegmentUrl(seg)
    const resp = await fetch(url)
    if (!resp.ok) {
      throw new Error(`下载单支图片失败: ${resp.status}`)
    }

    const blob = await resp.blob()
    const filename = getSegmentName(seg)
    const file = new File([blob], filename, { type: blob.type || 'image/png' })

    const result = await imageStore.uploadImage(file)
    await handleImageUploaded({ ...result, file })

    ElMessage.success('单支图片加载成功')
  } catch (error) {
    console.error('加载单支图片失败:', error)
    handleApiError(error, '加载单支图片失败')
  }
}

/**
 * 加载已上传的图像列表
 */
async function loadUploadedImages() {
  try {
    const images = await imageProcessingAPI.listImages(10)
    uploadedImages.value = images
    console.log('已加载图像列表:', images.length)
  } catch (error) {
    console.error('加载图像列表失败:', error)
  }
}

async function loadSlipSegments() {
  try {
    const segments = await imageProcessingAPI.listSegments({
      segment_type: 'slip',
      limit: 10,
      offset: 0
    })
    slipSegments.value = segments
    console.log('已加载单支切割结果:', segments.length)
  } catch (error) {
    console.error('加载单支切割结果失败:', error)
  }
}

/**
 * 选择已上传的图像
 */
async function handleSelectUploadedImage(img) {
  try {
    console.log('选择图像:', img)
    
    // 更新 store
    imageStore.currentImage = {
      image_id: img.image_id,
      filename: img.filename,
      width: img.width,
      height: img.height,
      format: img.format,
      file_size: img.file_size
    }
    imageStore.imageUrl = getImageUrl(img.image_id)
    
    // 确保 Canvas 已初始化
    await nextTick()
    if (!canvasHelper) {
      initCanvas()
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    
    // 加载图像到 Canvas
    const imageUrl = getImageUrl(img.image_id)
    console.log('开始加载图像:', imageUrl)
    await canvasHelper.loadImage(imageUrl)
    
    ElMessage.success('图像加载成功')
  } catch (error) {
    console.error('加载图像失败:', error)
    handleApiError(error, '加载图像失败')
  }
}

/**
 * 获取图像 URL
 */
function getImageUrl(imageId) {
  return imageProcessingAPI.getImageUrl(imageId)
}
/**
 * 工具点击
 */
function handleToolClick(toolKey) {
  activeTool.value = toolKey

  switch (toolKey) {
    case 'select':
      canvasHelper.setSelectionEnabled(true)
      break
    case 'delete':
      handleDeleteSelected()
      break
    case 'zoomIn':
      handleZoom(1.2)
      break
    case 'zoomOut':
      handleZoom(0.8)
      break
  }
}

/**
 * 自动检测
 */
async function handleDetect() {
  if (processingMode.value === 'manual') return
  try {
    let result
    // 构建检测参数，包含 model_type
    const detectParams = {
      ...(segmentationMode.value === 'single-slip' ? slipParams.value : charParams.value),
      model_type: selectedEngine.value
    }

    // 根据 useFastDetection 选择检测方式
    if (useFastDetection.value) {
      // 快速检测（同步）
      if (segmentationMode.value === 'single-slip') {
        result = await imageStore.detectSlipsFast(detectParams)
      } else {
        result = await imageStore.detectCharactersFast(detectParams)
      }
    } else {
      // 异步检测（Celery）
      if (segmentationMode.value === 'single-slip') {
        result = await imageStore.detectSlips(detectParams)
      } else {
        result = await imageStore.detectCharacters(detectParams)
      }
    }

    const detections = Array.isArray(result?.detections) ? result.detections : []
    const totalCount = typeof result?.total_count === 'number' ? result.total_count : detections.length
    console.info('[自动检测] 收到: total_count=%s, detections.length=%s, 模式=%s', totalCount, detections.length, useFastDetection.value ? '快速' : '异步', detections[0])

    canvasHelper.clearBoundingBoxes()
    if (detections.length > 0) {
      if (!canvasHelper.backgroundImage) {
        ElMessage.warning('画布未加载图像，检测框可能无法正确显示，请先选择图像')
      }
      canvasHelper.addBoundingBoxes(detections)
      await nextTick()
      canvasHelper.canvas.requestRenderAll()
      ElMessage.success(`检测完成，找到 ${totalCount} 个区域${useFastDetection.value ? '（快速模式）' : ''}`)
    } else {
      ElMessage.warning('未检测到任何区域，请调整参数后重试')
    }
  } catch (error) {
    handleApiError(error, '检测失败')
  }
}

/**
 * 手动添加框
 */
function handleAddBox() {
  if (!canvasHelper) {
    ElMessage.warning('请先加载图像')
    return
  }

  const existing = canvasHelper.getBoundingBoxes()
  const prefix = segmentationMode.value === 'single-character' ? 'char' : 'bbox'

  // 直接在画布上添加一个覆盖全图高度的“大框”，再由用户拖动调节，
  // 避免受绘制交互或坐标缩放的限制导致“最大框很小”的问题。
  const img = imageStore.currentImage
  const newBox = {
    id: `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2, 6)}`,
    order: existing.length + 1,
    x: 0,
    y: 0,
    width: img?.width || 2000,
    height: img?.height || 2000
  }

  canvasHelper.addBoundingBox(newBox)
  ElMessage.info('已添加一个大边界框，可拖动和缩放调整到合适位置')
}

/**
 * 引擎变化处理
 */
function handleEngineChange({ engine, params }) {
  console.log('[引擎切换] engine=%s, params=%o', engine, params)
  // 可以根据引擎自动更新 SAHI 参数
}

/**
 * 执行切割
 */
async function handleCut() {
  try {
    // 获取当前的边界框
    const boundingBoxes = canvasHelper.getBoundingBoxes()

    if (boundingBoxes.length === 0) {
      ElMessage.warning('请先检测或添加边界框')
      return
    }

    // 执行切割
    const result = await imageStore.cutImage(boundingBoxes, {
      outputFormat: 'png',
      addPadding: false,
      paddingSize: 10,
      // 只有在“图像来源为单支 + 单字切割模式”时，才需要把父级单支的 segment_id 传给后端
      parentSegmentId:
        imageSource.value === 'slip' && segmentationMode.value === 'single-character'
          ? currentSlipSegment.value?.segment_id
          : null
    })

    ElMessage.success(`切割完成，生成 ${result.total_count} 个文件`)
    // 若刚完成单支切割，刷新可选单支图片列表，便于继续联调
    if (segmentationMode.value === 'single-slip') {
      loadSlipSegments()
    }
    showResultsDialog.value = true
  } catch (error) {
    handleApiError(error, '切割失败')
  }
}

/**
 * 清空检测框
 */
function handleClearDetections() {
  ElMessageBox.confirm('确定要清空所有检测框吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    canvasHelper.clearBoundingBoxes()
    imageStore.updateDetectionResults([])
    ElMessage.success('已清空检测框')
  }).catch(() => {})
}

/**
 * 删除选中的边界框
 */
function handleDeleteSelected() {
  canvasHelper.removeSelectedBoxes()
  const updatedBoxes = canvasHelper.getBoundingBoxes()
  imageStore.updateDetectionResults(updatedBoxes)
}

/**
 * 删除指定边界框
 */
function handleDeleteBox(id) {
  canvasHelper.removeBoundingBox(id)
  const updatedBoxes = canvasHelper.getBoundingBoxes()
  imageStore.updateDetectionResults(updatedBoxes)
}

/**
 * 缩放
 */
function handleZoom(scale) {
  canvasHelper.zoom(scale)
}

/**
 * 适应画布
 */
function handleFitCanvas() {
  canvasHelper.fitToCanvas()
}

/**
 * 下载单个结果
 */
function handleDownload() {
  if (!segmentationResults.value) return
  showResultsDialog.value = true
}

/**
 * 下载所有结果
 */
function handleDownloadAll() {
  ElMessage.info('批量下载功能开发中...')
}

/**
 * 获取结果图像URL
 * 优先使用后端返回的 public_url（Supabase），否则回退到本地结果路径
 */
function getResultImageUrl(result) {
  if (result.public_url) {
    return result.public_url
  }
  if (result.path) {
    return `http://127.0.0.1:8000/${result.path}`
  }
  return ''
}

/**
 * 重新开始
 */
function handleReset() {
  ElMessageBox.confirm('确定要重新开始吗？这将清空当前所有数据。', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    canvasHelper.clear()
    imageStore.clearAll()
    segmentationMode.value = 'single-slip'
    imageSource.value = 'raw'
    currentSlipSegment.value = null
    showResultsDialog.value = false
    loadUploadedImages()
    loadSlipSegments()
    ElMessage.success('已重置')
  }).catch(() => {})
}

/**
 * 查看元数据（跳转到 Metadata 页面）
 */
function handleViewMetadata(segmentId) {
  router.push({
    name: 'Metadata',
    query: { segment_id: segmentId }
  })
}
</script>

<style scoped>
.seg-page {
  width: 100%;
}

.seg-page__container {
  max-width: 1400px;
  margin: 0 auto;
}

.seg-page__header {
  padding: 6px 2px 8px;
}

.seg-page__title {
  font-size: 22px;
  font-weight: 800;
  color: #1f2d3d;
  letter-spacing: 0.6px;
}

.seg-page__subtitle {
  margin-top: 6px;
  font-size: 12px;
  color: rgba(31, 45, 61, 0.62);
  letter-spacing: 0.35px;
}

.seg-page__section {
  margin-top: 18px;
}

.seg-workbench {
  align-items: stretch;
  min-height: 580px;
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

/* 工具栏样式 */
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

/* 工作区样式 */
.workspace-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.workspace {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.workspace__stage {
  position: relative;
  width: 100%;
  height: 600px; /* 必须显式给定高度 */
  background: #f5f5f5;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.workspace__stage canvas {
  width: 100% !important;
  height: 100% !important;
}

.workspace__placeholder {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  pointer-events: none;
  z-index: 1;
}

.workspace__placeholder-text {
  font-size: 14px;
  color: #999;
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

/* 控制面板样式 */
.control-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.control-panel__section {
  margin-bottom: 16px;
}

.control-panel__label {
  font-size: 13px;
  font-weight: 800;
  color: rgba(31, 45, 61, 0.80);
  margin-bottom: 12px;
}

.mode-radio {
  width: 100%;
}

.mode-radio :deep(.el-radio) {
  width: 100%;
  margin-right: 0;
  margin-bottom: 8px;
}

.control-panel__actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: auto;
}

:deep(.el-form-item) {
  margin-bottom: 12px;
}

:deep(.el-divider) {
  margin: 16px 0;
}

.control-panel__count {
  color: #409EFF;
  font-weight: 700;
}

.control-panel__hint {
  font-size: 12px;
  color: rgba(31, 45, 61, 0.65);
  line-height: 1.5;
}

.control-panel__hint--slip {
  padding: 10px 12px;
  background: rgba(64, 158, 255, 0.06);
  border-radius: 8px;
  border: 1px solid rgba(64, 158, 255, 0.15);
}

.detection-list {
  max-height: 200px;
  overflow-y: auto;
}

.detection-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 8px;
  background: rgba(31, 45, 61, 0.03);
  border: 1px solid rgba(31, 45, 61, 0.1);
  margin-bottom: 8px;
}

.detection-item:last-child {
  margin-bottom: 0;
}

.detection-item__order {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #409EFF;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.detection-item__info {
  flex: 1;
  font-size: 12px;
}

.detection-item__size {
  font-weight: 700;
  color: #1f2d3d;
  margin-bottom: 2px;
}

.detection-item__confidence {
  color: rgba(31, 45, 61, 0.6);
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
  max-height: 60vh;
  overflow-y: auto;
  padding: 10px;
}

.result-item {
  border: 1px solid rgba(31, 45, 61, 0.1);
  border-radius: 8px;
  overflow: hidden;
  background: white;
  transition: all 0.3s;
}

.result-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.result-item__order {
  position: absolute;
  top: 8px;
  left: 8px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #409EFF;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  z-index: 1;
}

.result-item__image {
  width: 100%;
  height: 150px;
  object-fit: contain;
  background: #f5f5f5;
  padding: 10px;
}

.result-item__info {
  padding: 8px;
  font-size: 11px;
  color: rgba(31, 45, 61, 0.7);
  text-align: center;
}

.result-item__filename {
  margin-top: 4px;
  font-size: 10px;
  color: rgba(31, 45, 61, 0.5);
  word-break: break-all;
}

.result-item__actions {
  margin-top: 8px;
}

/* 已上传图像列表 */
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
  max-height: 300px;
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
  border-color: #409EFF;
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
  .seg-page__container {
    max-width: 100%;
  }

  .seg-workbench {
    min-height: 520px;
  }

  .workspace__stage {
    height: 500px;
  }
}

@media (max-width: 768px) {
  .seg-page__header {
    padding: 4px 2px 6px;
  }

  .seg-page__title {
    font-size: 18px;
  }

  .seg-page__subtitle {
    font-size: 11px;
  }

  .seg-workbench {
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
    height: 400px;
  }

  .workspace-header {
    flex-direction: column;
    gap: 8px;
  }

  .control-panel__label {
    font-size: 12px;
  }

  .mode-radio :deep(.el-radio) {
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

  .workspace__footer {
    flex-wrap: wrap;
  }

  .workspace__status {
    flex-basis: 50%;
  }
}
</style>
