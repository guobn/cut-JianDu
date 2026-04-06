<template>
  <div class="recognition-verify">
    <!-- 顶部栏 -->
    <div class="verify-header">
      <div class="header-left">
        <el-button @click="goBack" size="large">← 返回</el-button>
      </div>
      <div class="header-center">
        <span class="group-name">{{ groupName }}</span>
        <span class="stage-label">阶段：{{ stage === 'slip' ? '单支校验' : '单字校验' }}</span>
        <span class="progress-label">进度：{{ validatedCount }}/{{ totalCount }}</span>
      </div>
      <div class="header-right">
        <el-button type="success" @click="validateAll" :disabled="validatedCount === totalCount">
          完成全组
        </el-button>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="verify-content">
      <!-- 左侧：图片列表 -->
      <div class="image-list-panel">
        <div class="list-header">
          <h4>图片列表</h4>
        </div>
        <div class="image-list">
          <div
            v-for="image in images"
            :key="image.id"
            :class="['image-item', { 'current': currentImageId === image.id, 'validated': isImageValidated(image.id) }]"
            @click="selectImage(image.id)"
          >
            <span class="image-name">{{ getImageName(image.filename) }}</span>
            <span class="image-status">
              {{ isImageValidated(image.id) ? '✓' : (currentImageId === image.id ? '→' : '○') }}
            </span>
          </div>
        </div>
      </div>

      <!-- 右侧：Canvas 区域 -->
      <div class="canvas-panel">
        <div class="canvas-toolbar">
          <el-button @click="deleteSelectedBox" :disabled="!selectedBoxId" size="small">删除选中框</el-button>
          <el-button @click="toggleAddMode" :type="addMode ? 'primary' : 'default'" size="small">添加框</el-button>
          <el-radio-group v-model="zoomLevel" size="small">
            <el-radio-button label="50">50%</el-radio-button>
            <el-radio-button label="75">75%</el-radio-button>
            <el-radio-button label="100">100%</el-radio-button>
            <el-radio-button label="fit">适应</el-radio-button>
          </el-radio-group>
        </div>
        <div class="canvas-container" ref="canvasContainer">
          <canvas
            ref="canvasRef"
            @mousedown="handleMouseDown"
            @mousemove="handleMouseMove"
            @mouseup="handleMouseUp"
            @dblclick="handleDoubleClick"
          ></canvas>
        </div>
      </div>
    </div>

    <!-- 底部操作栏 -->
    <div class="verify-footer">
      <el-button @click="prevImage" :disabled="!hasPrevImage">上一张</el-button>
      <el-button type="primary" @click="validateCurrentImage">此图校验完成，下一张</el-button>
      <el-button @click="nextImage" :disabled="!hasNextImage">下一张</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { groupsAPI } from '@/api/groups'
import { handleApiError } from '@/utils/errorHandler'

const router = useRouter()
const route = useRoute()

// 状态
const groupId = computed(() => route.params.groupId)
const stage = computed(() => route.params.stage) // 'slip' | 'char'

const images = ref([])
const currentImageId = ref(null)
const boxes = ref([]) // { id, x, y, width, height, selected }
const selectedBoxId = ref(null)
const addMode = ref(false)
const zoomLevel = ref('fit')

// Canvas 相关
const canvasRef = ref(null)
const canvasContainer = ref(null)
let ctx = null
let img = null
let scale = 1
let isDragging = false
let isResizing = false
let dragStartX = 0
let dragStartY = 0
let activeBoxIndex = -1
let resizeHandle = null // 'nw', 'ne', 'sw', 'se'

// 计算属性
const groupName = computed(() => {
  const group = images.value.find(i => i.group_name)
  return group?.group_name || '图像组'
})

const validatedImages = computed(() => {
  return images.value.filter(img => isImageValidated(img.id))
})

const validatedCount = computed(() => validatedImages.value.length)
const totalCount = computed(() => images.value.length)

const currentImage = computed(() => {
  return images.value.find(i => i.id === currentImageId.value)
})

const currentIndex = computed(() => {
  return images.value.findIndex(i => i.id === currentImageId.value)
})

const hasPrevImage = computed(() => currentIndex.value > 0)
const hasNextImage = computed(() => currentIndex.value < images.value.length - 1)

// 方法
const loadImages = async () => {
  try {
    const response = await groupsAPI.getGroupImages(groupId.value)
    images.value = response.data || []
    if (images.value.length > 0 && !currentImageId.value) {
      selectImage(images.value[0].id)
    }
  } catch (error) {
    handleApiError(error, '加载图片列表失败')
  }
}

const selectImage = async (imageId) => {
  currentImageId.value = imageId
  selectedBoxId.value = null
  await loadSegments(imageId)
  await loadImageToCanvas(imageId)
}

const loadSegments = async (imageId) => {
  try {
    const response = await groupsAPI.getGroupSegments(groupId.value, {
      sourceImageId: imageId,
      type: stage.value
    })
    boxes.value = (response.data || []).map(seg => ({
      id: seg.id,
      x: seg.bbox_x,
      y: seg.bbox_y,
      width: seg.bbox_width,
      height: seg.bbox_height,
      selected: false,
      validated: seg.validated
    }))
  } catch (error) {
    handleApiError(error, '加载检测框失败')
  }
}

const loadImageToCanvas = async (imageId) => {
  if (!canvasRef.value) return

  const image = images.value.find(i => i.id === imageId)
  if (!image) return

  img = new Image()
  img.onload = () => {
    const canvas = canvasRef.value
    const container = canvasContainer.value

    // 计算缩放
    const containerWidth = container.clientWidth - 20
    const containerHeight = container.clientHeight - 20

    if (zoomLevel.value === 'fit') {
      scale = Math.min(containerWidth / img.width, containerHeight / img.height)
    } else {
      scale = parseInt(zoomLevel.value) / 100
    }

    canvas.width = img.width * scale
    canvas.height = img.height * scale

    redraw()
  }
  img.src = image.file_url
}

const redraw = () => {
  if (!ctx || !img) return

  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  ctx.drawImage(img, 0, 0, canvasRef.value.width, canvasRef.value.height)

  for (const box of boxes.value) {
    ctx.strokeStyle = box.selected ? '#FFFF00' : '#00FF00'
    ctx.lineWidth = 2
    ctx.strokeRect(box.x * scale, box.y * scale, box.width * scale, box.height * scale)

    if (box.selected) {
      drawResizeHandles(box)
    }
  }
}

const drawResizeHandles = (box) => {
  const handles = [
    { x: box.x, y: box.y, cursor: 'nw-resize', name: 'nw' },
    { x: box.x + box.width, y: box.y, cursor: 'ne-resize', name: 'ne' },
    { x: box.x, y: box.y + box.height, cursor: 'sw-resize', name: 'sw' },
    { x: box.x + box.width, y: box.y + box.height, cursor: 'se-resize', name: 'se' }
  ]

  ctx.fillStyle = '#FFFFFF'
  ctx.strokeStyle = '#FFFF00'
  ctx.lineWidth = 1

  for (const h of handles) {
    const hx = h.x * scale
    const hy = h.y * scale
    ctx.fillRect(hx - 4, hy - 4, 8, 8)
    ctx.strokeRect(hx - 4, hy - 4, 8, 8)
  }
}

const getImageName = (filename) => {
  if (!filename) return '未命名'
  return filename.length > 20 ? filename.substring(0, 17) + '...' : filename
}

const isImageValidated = (imageId) => {
  const imageBoxes = boxes.value.filter(b => {
    // 由于 boxes 是按当前 image 加载的，需要检查
    return true
  })
  // 这里需要根据实际数据判断
  return false
}

const handleMouseDown = (e) => {
  if (!img) return

  const rect = canvasRef.value.getBoundingClientRect()
  const mouseX = (e.clientX - rect.left) / scale
  const mouseY = (e.clientY - rect.top) / scale

  if (addMode.value) {
    // 添加新框模式
    const newBox = {
      id: null, // 新建的框还没有 id
      x: mouseX,
      y: mouseY,
      width: 0,
      height: 0,
      selected: true,
      isNew: true
    }
    boxes.value.forEach(b => b.selected = false)
    boxes.value.push(newBox)
    selectedBoxId.value = null
    isDragging = true
    dragStartX = mouseX
    dragStartY = mouseY
    activeBoxIndex = boxes.value.length - 1
    addMode.value = false
    return
  }

  // 检查是否点击了某个框
  for (let i = boxes.value.length - 1; i >= 0; i--) {
    const box = boxes.value[i]
    if (isPointInBox(mouseX, mouseY, box)) {
      // 检查是否点击了调整手柄
      const handle = getResizeHandle(mouseX, mouseY, box)
      if (handle) {
        isResizing = true
        resizeHandle = handle
        activeBoxIndex = i
      } else {
        isDragging = true
        dragStartX = mouseX - box.x
        dragStartY = mouseY - box.y
        activeBoxIndex = i
      }
      boxes.value.forEach(b => b.selected = false)
      box.selected = true
      selectedBoxId.value = box.id
      redraw()
      return
    }
  }

  // 点击空白区域，取消选择
  boxes.value.forEach(b => b.selected = false)
  selectedBoxId.value = null
  redraw()
}

const handleMouseMove = (e) => {
  if (!img || activeBoxIndex < 0) return

  const rect = canvasRef.value.getBoundingClientRect()
  const mouseX = (e.clientX - rect.left) / scale
  const mouseY = (e.clientY - rect.top) / scale

  if (isDragging) {
    const box = boxes.value[activeBoxIndex]
    box.x = mouseX - dragStartX
    box.y = mouseY - dragStartY
    redraw()
  } else if (isResizing) {
    const box = boxes.value[activeBoxIndex]
    switch (resizeHandle) {
      case 'nw':
        box.width += box.x - mouseX
        box.height += box.y - mouseY
        box.x = mouseX
        box.y = mouseY
        break
      case 'ne':
        box.width = mouseX - box.x
        box.height += box.y - mouseY
        box.y = mouseY
        break
      case 'sw':
        box.width += box.x - mouseX
        box.x = mouseX
        box.height = mouseY - box.y
        break
      case 'se':
        box.width = mouseX - box.x
        box.height = mouseY - box.y
        break
    }
    redraw()
  }
}

const handleMouseUp = async () => {
  if (isDragging || isResizing) {
    const box = boxes.value[activeBoxIndex]
    if (box.id && !box.isNew) {
      // 保存更新
      await saveBoxUpdate(box)
    }
  }

  isDragging = false
  isResizing = false
  resizeHandle = null
  activeBoxIndex = -1
}

const handleDoubleClick = async (e) => {
  if (!img) return

  const rect = canvasRef.value.getBoundingClientRect()
  const mouseX = (e.clientX - rect.left) / scale
  const mouseY = (e.clientY - rect.top) / scale

  // 检查是否双击了某个框
  for (let i = boxes.value.length - 1; i >= 0; i--) {
    const box = boxes.value[i]
    if (isPointInBox(mouseX, mouseY, box)) {
      if (box.id && !box.isNew) {
        // 删除框
        await deleteBox(box)
      }
      return
    }
  }
}

const isPointInBox = (px, py, box) => {
  return px >= box.x && px <= box.x + box.width && py >= box.y && py <= box.y + box.height
}

const getResizeHandle = (px, py, box) => {
  const handles = [
    { x: box.x, y: box.y, name: 'nw' },
    { x: box.x + box.width, y: box.y, name: 'ne' },
    { x: box.x, y: box.y + box.height, name: 'sw' },
    { x: box.x + box.width, y: box.y + box.height, name: 'se' }
  ]

  for (const h of handles) {
    if (Math.abs(px - h.x) < 8 && Math.abs(py - h.y) < 8) {
      return h.name
    }
  }
  return null
}

const saveBoxUpdate = async (box) => {
  try {
    await groupsAPI.updateSegment(groupId.value, box.id, {
      bbox_x: Math.round(box.x),
      bbox_y: Math.round(box.y),
      bbox_width: Math.round(box.width),
      bbox_height: Math.round(box.height)
    })
  } catch (error) {
    handleApiError(error, '保存框失败')
  }
}

const deleteBox = async (box) => {
  try {
    await groupsAPI.deleteSegment(groupId.value, box.id)
    boxes.value = boxes.value.filter(b => b.id !== box.id)
    if (selectedBoxId.value === box.id) {
      selectedBoxId.value = null
    }
    redraw()
  } catch (error) {
    handleApiError(error, '删除框失败')
  }
}

const deleteSelectedBox = async () => {
  const box = boxes.value.find(b => b.id === selectedBoxId.value)
  if (box) {
    await deleteBox(box)
  }
}

const toggleAddMode = () => {
  addMode.value = !addMode.value
}

const prevImage = async () => {
  if (hasPrevImage.value) {
    await selectImage(images.value[currentIndex.value - 1].id)
  }
}

const nextImage = async () => {
  if (hasNextImage.value) {
    await selectImage(images.value[currentIndex.value + 1].id)
  }
}

const validateCurrentImage = async () => {
  // 将当前图片的所有框标记为已校验
  for (const box of boxes.value) {
    if (box.id && !box.validated) {
      try {
        await groupsAPI.updateSegment(groupId.value, box.id, { validated: true })
        box.validated = true
      } catch (error) {
        handleApiError(error, '标记校验失败')
      }
    }
  }

  ElMessage.success('当前图片校验完成')

  // 自动跳转到下一张
  if (hasNextImage.value) {
    await nextImage()
  }
}

const validateAll = () => {
  ElMessage.info('完成全组功能开发中')
}

const goBack = () => {
  router.push(`/batch-segmentation?groupId=${groupId.value}&${stage}Done=true`)
}

const handleZoomChange = () => {
  nextTick(() => {
    loadImageToCanvas(currentImageId.value)
  })
}

// 监听 zoomLevel 变化
watch(zoomLevel, handleZoomChange)

// 初始化
onMounted(async () => {
  await loadImages()
})
</script>

<style scoped lang="scss">
.recognition-verify {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f0e8;
}

.verify-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 20px;
  background: white;
  border-bottom: 1px solid #ddd;

  .header-center {
    display: flex;
    gap: 30px;
    align-items: center;

    .group-name {
      font-size: 18px;
      font-weight: bold;
    }

    .stage-label, .progress-label {
      font-size: 14px;
      color: #666;
    }
  }
}

.verify-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.image-list-panel {
  width: 260px;
  background: white;
  border-right: 1px solid #ddd;
  display: flex;
  flex-direction: column;

  .list-header {
    padding: 15px;
    border-bottom: 1px solid #eee;

    h4 {
      margin: 0;
      font-size: 16px;
    }
  }

  .image-list {
    flex: 1;
    overflow-y: auto;
    padding: 10px;
  }

  .image-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px;
    margin-bottom: 5px;
    border-radius: 4px;
    cursor: pointer;
    background: #f5f5f5;

    &.current {
      background: #e6f0ff;
      border-left: 3px solid #409eff;
    }

    &.validated {
      color: #67c23a;
    }

    .image-name {
      font-size: 13px;
    }

    .image-status {
      font-weight: bold;
    }
  }
}

.canvas-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 15px;

  .canvas-toolbar {
    display: flex;
    gap: 10px;
    margin-bottom: 10px;
  }

  .canvas-container {
    flex: 1;
    background: #333;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;

    canvas {
      cursor: crosshair;
    }
  }
}

.verify-footer {
  display: flex;
  justify-content: center;
  gap: 20px;
  padding: 15px;
  background: white;
  border-top: 1px solid #ddd;
}
</style>
