<template>
  <div class="test-page">
    <div class="test-header">
      <h1>🧪 简牍图像处理核心功能测试</h1>
      <p class="test-subtitle">集成测试：单支切割 | 单字切割 | 旋转校正 | 尺寸归一化</p>
    </div>

    <el-card class="test-card">
      <!-- 图像上传区域 -->
      <div class="upload-section">
        <h3>📤 1. 上传测试图像</h3>
        <el-upload
          ref="uploadRef"
          class="upload-demo"
          drag
          :auto-upload="false"
          :show-file-list="false"
          :on-change="handleFileChange"
          accept="image/jpeg,image/png,image/tiff,image/bmp"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            拖拽图像到此处或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">支持 JPG、PNG、TIFF、BMP 格式，最大 50MB</div>
          </template>
        </el-upload>

        <el-button
          v-if="selectedFile"
          type="primary"
          :loading="uploading"
          @click="uploadImage"
          style="margin-top: 10px"
        >
          确认上传
        </el-button>

        <div v-if="currentImage" class="image-info">
          <el-tag type="success">✓ 已上传</el-tag>
          <span>{{ currentImage.filename }} ({{ currentImage.width }}×{{ currentImage.height }})</span>
        </div>
      </div>

      <!-- 图像预览和Canvas区域 -->
      <div v-if="currentImage" class="preview-section">
        <h3>🖼️ 图像预览与检测结果</h3>
        <div class="canvas-container">
          <canvas ref="canvasRef" id="testCanvas"></canvas>
        </div>
      </div>

      <!-- 功能测试区域 -->
      <div v-if="currentImage" class="function-section">
        <el-tabs v-model="activeTab" type="border-card">
          <!-- 单支切割 -->
          <el-tab-pane label="🔪 单支切割" name="slip">
            <div class="tab-content">
              <el-form :inline="true">
                <el-form-item label="检测模型">
                  <el-select v-model="slipModel" style="width: 200px">
                    <el-option label="YOLOv8 (推荐)" value="yolov8" />
                    <el-option label="APS-YOLO" value="aps-yolo" />
                    <el-option label="DeConv-YOLO" value="deconv-yolo" />
                    <el-option label="YOLOv12" value="yolov12" />
                  </el-select>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="detecting" @click="detectSlips">
                    自动检测单支
                  </el-button>
                  <el-button :disabled="!detectionResult" @click="executeSlipCut">
                    执行切割 ({{ detectionResult?.total_count || 0 }} 个)
                  </el-button>
                  <el-button @click="clearDetection">清除检测框</el-button>
                </el-form-item>
              </el-form>

              <div v-if="slipCutResult" class="result-box">
                <el-alert type="success" :closable="false">
                  <template #title>
                    ✓ 切割完成！共切割 {{ slipCutResult.results?.length || 0 }} 个单支
                  </template>
                </el-alert>
                <div class="result-images">
                  <div
                    v-for="(result, index) in slipCutResult.results"
                    :key="index"
                    class="result-item"
                  >
                    <img :src="getImageUrl(result.output_path)" :alt="`单支 ${index + 1}`" />
                    <span>单支 {{ index + 1 }}</span>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- 单字切割 -->
          <el-tab-pane label="✂️ 单字切割" name="char">
            <div class="tab-content">
              <el-form :inline="true">
                <el-form-item label="检测模型">
                  <el-select v-model="charModel" style="width: 200px">
                    <el-option label="RGA-CRNN (推荐)" value="rga-crnn" />
                    <el-option label="TorchScript" value="torchscript" />
                  </el-select>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="detecting" @click="detectChars">
                    自动检测单字
                  </el-button>
                  <el-button :disabled="!detectionResult" @click="executeCharCut">
                    执行切割 ({{ detectionResult?.total_count || 0 }} 个)
                  </el-button>
                  <el-button @click="clearDetection">清除检测框</el-button>
                </el-form-item>
              </el-form>

              <div v-if="charCutResult" class="result-box">
                <el-alert type="success" :closable="false">
                  <template #title>
                    ✓ 切割完成！共切割 {{ charCutResult.results?.length || 0 }} 个单字
                  </template>
                </el-alert>
                <div class="result-images">
                  <div
                    v-for="(result, index) in charCutResult.results"
                    :key="index"
                    class="result-item"
                  >
                    <img :src="getImageUrl(result.output_path)" :alt="`单字 ${index + 1}`" />
                    <span>字 {{ index + 1 }}</span>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- 旋转校正 -->
          <el-tab-pane label="🔄 旋转校正" name="rotation">
            <div class="tab-content">
              <el-form :inline="true">
                <el-form-item label="旋转角度">
                  <el-input-number
                    v-model="rotationAngle"
                    :min="-180"
                    :max="180"
                    :step="0.1"
                    style="width: 150px"
                  />
                </el-form-item>
                <el-form-item label="自动裁剪">
                  <el-switch v-model="autoCrop" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="processing" @click="detectRotation">
                    自动检测角度
                  </el-button>
                  <el-button type="success" :loading="processing" @click="correctRotation">
                    执行校正
                  </el-button>
                </el-form-item>
              </el-form>

              <div v-if="rotationDetectResult" class="result-box">
                <el-alert type="info" :closable="false">
                  检测到旋转角度: {{ rotationDetectResult.angle?.toFixed(2) }}°
                  (置信度: {{ (rotationDetectResult.confidence * 100).toFixed(1) }}%)
                </el-alert>
              </div>

              <div v-if="rotationResult" class="result-box">
                <el-alert type="success" :closable="false">
                  <template #title>
                    ✓ 旋转校正完成！角度: {{ rotationResult.angle?.toFixed(2) }}°
                  </template>
                </el-alert>
                <div class="result-images">
                  <div class="result-item large">
                    <img :src="getImageUrl(rotationResult.output_path)" alt="校正后" />
                    <span>校正后图像</span>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- 尺寸归一化 -->
          <el-tab-pane label="📏 尺寸归一化" name="normalization">
            <div class="tab-content">
              <el-form :inline="true">
                <el-form-item label="目标宽度">
                  <el-input-number v-model="targetWidth" :min="100" :max="4000" style="width: 120px" />
                </el-form-item>
                <el-form-item label="目标高度">
                  <el-input-number v-model="targetHeight" :min="100" :max="4000" style="width: 120px" />
                </el-form-item>
                <el-form-item label="保持比例">
                  <el-switch v-model="keepAspectRatio" />
                </el-form-item>
                <el-form-item label="填充颜色">
                  <el-select v-model="paddingColor" style="width: 100px">
                    <el-option label="白色" value="white" />
                    <el-option label="黑色" value="black" />
                    <el-option label="灰色" value="gray" />
                  </el-select>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="processing" @click="normalizeSize">
                    执行归一化
                  </el-button>
                </el-form-item>
              </el-form>

              <div v-if="normalizationResult" class="result-box">
                <el-alert type="success" :closable="false">
                  <template #title>
                    ✓ 归一化完成！尺寸: {{ normalizationResult.output_width }}×{{ normalizationResult.output_height }}
                  </template>
                </el-alert>
                <div class="result-images">
                  <div class="result-item large">
                    <img :src="getImageUrl(normalizationResult.output_path)" alt="归一化后" />
                    <span>归一化后图像</span>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { handleApiError } from '@/utils/errorHandler'
import { UploadFilled } from '@element-plus/icons-vue'
import { fabric } from 'fabric'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_BACKEND_BASE_URL || 'http://127.0.0.1:8000'

// 状态
const uploadRef = ref(null)
const canvasRef = ref(null)
const selectedFile = ref(null)
const currentImage = ref(null)
const fabricCanvas = ref(null)
const activeTab = ref('slip')

// 加载状态
const uploading = ref(false)
const detecting = ref(false)
const processing = ref(false)

// 检测结果
const detectionResult = ref(null)
const slipCutResult = ref(null)
const charCutResult = ref(null)
const rotationDetectResult = ref(null)
const rotationResult = ref(null)
const normalizationResult = ref(null)

// 参数
const slipModel = ref('yolov8')
const charModel = ref('rga-crnn')
const rotationAngle = ref(0)
const autoCrop = ref(true)
const targetWidth = ref(800)
const targetHeight = ref(1200)
const keepAspectRatio = ref(true)
const paddingColor = ref('white')

// 文件选择
function handleFileChange(file) {
  selectedFile.value = file.raw
}

// 上传图像
async function uploadImage() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择图像文件')
    return
  }

  uploading.value = true
  const formData = new FormData()
  formData.append('file', selectedFile.value)

  try {
    const response = await axios.post(`${API_BASE_URL}/api/test/upload`, formData)
    currentImage.value = response.data
    ElMessage.success('图像上传成功')

    // 加载图像到Canvas
    await nextTick()
    await loadImageToCanvas(currentImage.value.image_id)
  } catch (error) {
    handleApiError(error, '上传失败')
  } finally {
    uploading.value = false
  }
}

// 加载图像到Canvas
async function loadImageToCanvas(imageId) {
  const imageUrl = `${API_BASE_URL}/api/test/image/${imageId}?t=${Date.now()}`

  return new Promise((resolve, reject) => {
    fabric.Image.fromURL(
      imageUrl,
      (img) => {
        if (!img) {
          reject(new Error('图像加载失败'))
          return
        }

        // 初始化Canvas
        if (!fabricCanvas.value) {
          fabricCanvas.value = new fabric.Canvas('testCanvas', {
            width: 1000,
            height: 700,
            backgroundColor: '#f5f5f5'
          })
        } else {
          fabricCanvas.value.clear()
        }

        // 计算缩放比例
        const maxWidth = 1000
        const maxHeight = 700
        const scale = Math.min(maxWidth / img.width, maxHeight / img.height, 1)

        img.scale(scale)
        img.set({
          left: (maxWidth - img.width * scale) / 2,
          top: (maxHeight - img.height * scale) / 2,
          selectable: false
        })

        fabricCanvas.value.add(img)
        fabricCanvas.value.renderAll()
        resolve()
      },
      { crossOrigin: 'anonymous' }
    )
  })
}

// 检测单支
async function detectSlips() {
  if (!selectedFile.value) {
    ElMessage.warning('请先上传图像')
    return
  }

  detecting.value = true
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('mode', 'single-slip')
  formData.append('model_type', slipModel.value)

  try {
    const response = await axios.post(`${API_BASE_URL}/api/test/detect`, formData)
    detectionResult.value = response.data
    ElMessage.success(`检测完成！发现 ${response.data.total_count} 个单支`)

    // 绘制检测框
    drawBoundingBoxes(response.data.detections)
  } catch (error) {
    handleApiError(error, '检测失败')
  } finally {
    detecting.value = false
  }
}

// 检测单字
async function detectChars() {
  if (!selectedFile.value) {
    ElMessage.warning('请先上传图像')
    return
  }

  detecting.value = true
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('mode', 'single-character')
  formData.append('model_type', charModel.value)

  try {
    const response = await axios.post(`${API_BASE_URL}/api/test/detect`, formData)
    detectionResult.value = response.data
    ElMessage.success(`检测完成！发现 ${response.data.total_count} 个单字`)

    // 绘制检测框
    drawBoundingBoxes(response.data.detections)
  } catch (error) {
    handleApiError(error, '检测失败')
  } finally {
    detecting.value = false
  }
}

// 绘制边界框
function drawBoundingBoxes(detections) {
  if (!fabricCanvas.value || !detections) return

  // 清除之前的边界框
  const objects = fabricCanvas.value.getObjects()
  objects.forEach((obj) => {
    if (obj.type === 'rect' && obj.name === 'bbox') {
      fabricCanvas.value.remove(obj)
    }
  })

  // 获取图像对象
  const imageObj = fabricCanvas.value.getObjects().find((obj) => obj.type === 'image')
  if (!imageObj) return

  const scale = imageObj.scaleX
  const offsetX = imageObj.left
  const offsetY = imageObj.top

  // 绘制新的边界框
  detections.forEach((detection, index) => {
    const rect = new fabric.Rect({
      left: offsetX + detection.x * scale,
      top: offsetY + detection.y * scale,
      width: detection.width * scale,
      height: detection.height * scale,
      fill: 'transparent',
      stroke: '#409EFF',
      strokeWidth: 2,
      selectable: false,
      name: 'bbox'
    })

    const text = new fabric.Text(`${index + 1}`, {
      left: offsetX + detection.x * scale + 5,
      top: offsetY + detection.y * scale + 5,
      fontSize: 14,
      fill: '#409EFF',
      selectable: false,
      name: 'bbox'
    })

    fabricCanvas.value.add(rect)
    fabricCanvas.value.add(text)
  })

  fabricCanvas.value.renderAll()
}

// 执行单支切割
async function executeSlipCut() {
  if (!detectionResult.value) {
    ElMessage.warning('请先执行检测')
    return
  }

  processing.value = true
  const formData = new FormData()
  formData.append('image_id', currentImage.value.image_id)
  formData.append('bounding_boxes', JSON.stringify(detectionResult.value.detections))
  formData.append('segment_type', 'slip')

  try {
    const response = await axios.post(`${API_BASE_URL}/api/test/cut`, formData)
    slipCutResult.value = response.data
    ElMessage.success(response.data.message)
  } catch (error) {
    handleApiError(error, '切割失败')
  } finally {
    processing.value = false
  }
}

// 执行单字切割
async function executeCharCut() {
  if (!detectionResult.value) {
    ElMessage.warning('请先执行检测')
    return
  }

  processing.value = true
  const formData = new FormData()
  formData.append('image_id', currentImage.value.image_id)
  formData.append('bounding_boxes', JSON.stringify(detectionResult.value.detections))
  formData.append('segment_type', 'char')

  try {
    const response = await axios.post(`${API_BASE_URL}/api/test/cut`, formData)
    charCutResult.value = response.data
    ElMessage.success(response.data.message)
  } catch (error) {
    handleApiError(error, '切割失败')
  } finally {
    processing.value = false
  }
}

// 检测旋转角度
async function detectRotation() {
  if (!selectedFile.value) {
    ElMessage.warning('请先上传图像')
    return
  }

  processing.value = true
  const formData = new FormData()
  formData.append('file', selectedFile.value)

  try {
    const response = await axios.post(`${API_BASE_URL}/api/test/rotation/detect`, formData)
    rotationDetectResult.value = response.data
    rotationAngle.value = response.data.angle
    ElMessage.success(`检测完成！角度: ${response.data.angle.toFixed(2)}°`)
  } catch (error) {
    handleApiError(error, '检测失败')
  } finally {
    processing.value = false
  }
}

// 旋转校正
async function correctRotation() {
  if (!selectedFile.value) {
    ElMessage.warning('请先上传图像')
    return
  }

  processing.value = true
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('angle', rotationAngle.value)
  formData.append('auto_crop', autoCrop.value)

  try {
    const response = await axios.post(`${API_BASE_URL}/api/test/rotation/correct`, formData)
    rotationResult.value = response.data
    ElMessage.success('旋转校正完成')
  } catch (error) {
    handleApiError(error, '校正失败')
  } finally {
    processing.value = false
  }
}

// 尺寸归一化
async function normalizeSize() {
  if (!selectedFile.value) {
    ElMessage.warning('请先上传图像')
    return
  }

  processing.value = true
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('target_width', targetWidth.value)
  formData.append('target_height', targetHeight.value)
  formData.append('keep_aspect_ratio', keepAspectRatio.value)
  formData.append('padding_color', paddingColor.value)

  try {
    const response = await axios.post(`${API_BASE_URL}/api/test/normalization/normalize`, formData)
    normalizationResult.value = response.data
    ElMessage.success('尺寸归一化完成')
  } catch (error) {
    handleApiError(error, '归一化失败')
  } finally {
    processing.value = false
  }
}

// 清除检测框
function clearDetection() {
  detectionResult.value = null
  if (fabricCanvas.value) {
    const objects = fabricCanvas.value.getObjects()
    objects.forEach((obj) => {
      if (obj.name === 'bbox') {
        fabricCanvas.value.remove(obj)
      }
    })
    fabricCanvas.value.renderAll()
  }
}

// 获取图像URL
function getImageUrl(path) {
  if (!path) return ''
  // 处理相对路径
  if (path.startsWith('./') || path.startsWith('../')) {
    return `${API_BASE_URL}/${path.replace(/^\.\.?\//, '')}`
  }
  return `${API_BASE_URL}/${path}`
}

onMounted(() => {
  // 初始化
})
</script>

<style scoped>
.test-page {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.test-header {
  text-align: center;
  margin-bottom: 30px;
}

.test-header h1 {
  font-size: 32px;
  color: #1f2d3d;
  margin-bottom: 10px;
}

.test-subtitle {
  font-size: 16px;
  color: #606266;
}

.test-card {
  margin-bottom: 20px;
}

.upload-section {
  margin-bottom: 30px;
}

.upload-section h3 {
  margin-bottom: 15px;
  color: #1f2d3d;
}

.image-info {
  margin-top: 15px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.preview-section {
  margin-bottom: 30px;
}

.preview-section h3 {
  margin-bottom: 15px;
  color: #1f2d3d;
}

.canvas-container {
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  justify-content: center;
  background: #f5f5f5;
}

.function-section {
  margin-top: 30px;
}

.tab-content {
  padding: 20px;
}

.result-box {
  margin-top: 20px;
}

.result-images {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 15px;
  margin-top: 15px;
}

.result-item {
  text-align: center;
}

.result-item.large {
  grid-column: span 2;
}

.result-item img {
  width: 100%;
  height: auto;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  object-fit: contain;
  max-height: 200px;
}

.result-item span {
  display: block;
  margin-top: 5px;
  font-size: 12px;
  color: #606266;
}

.el-icon--upload {
  font-size: 67px;
  color: #409eff;
  margin-bottom: 16px;
}

.el-upload__text {
  font-size: 14px;
  color: #606266;
}

.el-upload__text em {
  color: #409eff;
  font-style: normal;
}
</style>
