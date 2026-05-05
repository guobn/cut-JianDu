<template>
  <div class="batch-verify-page">
    <div class="verify-header">
      <div class="header-left">
        <el-button :icon="ArrowLeft" @click="handleBack">返回</el-button>
        <span class="header-title">{{ pageTitle }}</span>
      </div>
      <div class="header-center">
        <span class="group-name">组名: {{ groupName }}</span>
      </div>
      <div class="header-right">
        <span class="verify-count">已校验 {{ verifiedCount }}/{{ totalCount }}</span>
        <el-button type="primary" :disabled="!canConfirm" @click="handleConfirm">
          确认提交
        </el-button>
      </div>
    </div>

    <div class="verify-content">
      <div class="canvas-panel">
        <div class="canvas-header">
          <span>{{ canvasTitle }}</span>
          <div class="canvas-tools">
            <el-button-group size="small">
              <el-button @click="handleZoom(0.5)" :disabled="!imageLoaded">50%</el-button>
              <el-button @click="handleZoom(0.75)" :disabled="!imageLoaded">75%</el-button>
              <el-button type="primary" @click="handleZoom(1)" :disabled="!imageLoaded">100%</el-button>
              <el-button @click="handleFitCanvas" :disabled="!imageLoaded">适应</el-button>
            </el-button-group>
            <el-button-group size="small" style="margin-left: 12px;">
              <el-button @click="handlePrevImage" :disabled="currentImageIndex <= 0">
                <el-icon><ArrowLeft /></el-icon>
                上一张
              </el-button>
              <el-button @click="handleNextImage" :disabled="currentImageIndex >= verificationItems.length - 1">
                下一张
                <el-icon><ArrowRight /></el-icon>
              </el-button>
            </el-button-group>
            <span class="position-indicator">
              {{ currentImageIndex + 1 }} / {{ verificationItems.length }}
            </span>
          </div>
        </div>

        <div class="canvas-container" ref="canvasContainerRef">
          <canvas ref="canvasRef"></canvas>
          <div v-if="!imageLoaded" class="canvas-placeholder">
            <el-icon :size="48" color="#ccc"><Picture /></el-icon>
            <div>加载图像中...</div>
          </div>
        </div>

        <div class="canvas-footer">
          <div class="canvas-hint">
            <span v-if="isAddingBox">拖动绘制新框</span>
            <span v-else-if="selectedBox">已选中框 #{{ selectedBoxIndex + 1 }}，可拖动调整位置和大小</span>
            <span v-else>点击选中框，黄色高亮表示当前选中项</span>
          </div>
        </div>
      </div>

      <div class="thumbnails-panel">
        <div class="thumbnails-header">
          <span class="image-name">{{ currentImageName }}</span>
          <span class="detection-info">检测到 {{ totalCount }} 个框，已校验 {{ verifiedCount }}/{{ totalCount }}</span>
        </div>

        <div class="thumbnails-grid">
          <div
            v-for="(box, index) in boxes"
            :key="box.id"
            class="thumbnail-item"
            :class="{
              'thumbnail-item--selected': selectedBoxId === box.id,
              'thumbnail-item--verified': box.verified,
              'thumbnail-item--rejected': box.rejected
            }"
            @click="handleSelectBox(box.id)"
          >
            <div class="thumbnail-index">{{ index + 1 }}</div>
            <div class="thumbnail-status">
              <el-icon v-if="box.verified" color="#67C23A" :size="20"><Check /></el-icon>
              <el-icon v-else-if="box.rejected" color="#F56C6C" :size="20"><Close /></el-icon>
              <el-icon v-else color="#909399" :size="20"><QuestionFilled /></el-icon>
            </div>
            <div class="thumbnail-checkbox">
              <el-checkbox
                :model-value="box.selected"
                @click.stop
                @change="(val) => handleBatchSelect(box.id, val)"
              />
            </div>
          </div>
        </div>

        <div class="thumbnails-actions">
          <el-button @click="handleBatchDelete" :disabled="!hasSelectedBoxes">
            批量删除
          </el-button>
          <el-button type="primary" @click="handleAddNewBox" :disabled="isAddingBox">
            添加新框
          </el-button>
        </div>

        <div class="thumbnails-footer">
          <el-checkbox
            v-model="selectAll"
            :indeterminate="isIndeterminate"
            @change="handleSelectAll"
          >
            全选
          </el-checkbox>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, ArrowRight, Check, Close, Picture, QuestionFilled } from '@element-plus/icons-vue'

import { groupsAPI } from '@/api/groups'
import { handleApiError } from '@/utils/errorHandler'
import { useUserStore } from '@/store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const canvasContainerRef = ref(null)
const canvasRef = ref(null)

const groupId = computed(() => route.params.groupId)
const stage = computed(() => route.params.stage)
const isCharStage = computed(() => stage.value === 'char')
const pageTitle = computed(() => (isCharStage.value ? '批量切割 - 单字校验' : '批量切割 - 单支校验'))
const canvasTitle = computed(() => (isCharStage.value ? '单支图像 + 检测框叠加显示' : '原图 + 检测框叠加显示'))

const groupName = ref('')
const imageLoaded = ref(false)
const verificationItems = ref([])
const currentImageIndex = ref(0)
const currentImage = computed(() => verificationItems.value[currentImageIndex.value] || null)
const currentImageName = computed(() => currentImage.value?.filename || '')

let ctx = null
let canvasWidth = 800
let canvasHeight = 600
let scale = 1
let cachedImageElement = null
let naturalWidth = 0
let naturalHeight = 0

const boxes = ref([])
const selectedBoxId = ref(null)
const isAddingBox = ref(false)
const isDragging = ref(false)
const isResizing = ref(false)
const resizeHandle = ref(null)
const selectAll = ref(false)
const deletedBoxIds = ref(new Set())
const hasChanges = ref(false)

const dragState = ref({
  startX: 0,
  startY: 0,
  currentX: 0,
  currentY: 0,
  boxId: null,
  type: null,
  originalBox: null
})

const selectedBox = computed(() => boxes.value.find((b) => b.id === selectedBoxId.value))
const selectedBoxIndex = computed(() => boxes.value.findIndex((b) => b.id === selectedBoxId.value))
const totalCount = computed(() => boxes.value.length)
const verifiedCount = computed(() => boxes.value.filter((b) => b.verified).length)
const hasSelectedBoxes = computed(() => boxes.value.some((b) => b.selected))
const canConfirm = computed(() => imageLoaded.value && boxes.value.length > 0)
const isIndeterminate = computed(() => {
  const selected = boxes.value.filter((b) => b.selected).length
  return selected > 0 && selected < boxes.value.length
})

function toCanvasBox(seg, item) {
  if (!isCharStage.value) {
    return {
      x: seg.bbox_x,
      y: seg.bbox_y,
      width: seg.bbox_width,
      height: seg.bbox_height
    }
  }

  return {
    x: seg.bbox_x - (item.bbox_x || 0),
    y: seg.bbox_y - (item.bbox_y || 0),
    width: seg.bbox_width,
    height: seg.bbox_height
  }
}

function toPersistedBox(box) {
  if (!isCharStage.value) {
    return {
      bbox_x: box.x,
      bbox_y: box.y,
      bbox_width: box.width,
      bbox_height: box.height
    }
  }

  return {
    bbox_x: box.x + (currentImage.value?.bbox_x || 0),
    bbox_y: box.y + (currentImage.value?.bbox_y || 0),
    bbox_width: box.width,
    bbox_height: box.height
  }
}

onMounted(async () => {
  await loadGroupData()
  await loadVerificationItems()
  initCanvas()
})

onBeforeUnmount(() => {
  const canvas = canvasRef.value
  if (canvas) {
    canvas.removeEventListener('mousedown', handleCanvasMouseDown)
    canvas.removeEventListener('mousemove', handleCanvasMouseMove)
    canvas.removeEventListener('mouseup', handleCanvasMouseUp)
    canvas.removeEventListener('mouseleave', handleCanvasMouseUp)
  }
})

async function loadGroupData() {
  try {
    const group = await groupsAPI.getGroupDetail(groupId.value)
    groupName.value = group.name
  } catch (error) {
    handleApiError(error, '加载组信息失败')
  }
}

async function loadVerificationItems() {
  try {
    if (isCharStage.value) {
      const slips = await groupsAPI.getGroupSegments(groupId.value, {
        type: 'slip',
        validated: true
      })
      verificationItems.value = (slips || []).map((slip, index) => ({
        ...slip,
        filename: `单支 ${index + 1}`,
        original_source_image_id: slip.source_image_id
      }))
    } else {
      const result = await groupsAPI.getGroupImages(groupId.value, 1, 200)
      verificationItems.value = result.items || []
    }

    currentImageIndex.value = 0
    if (verificationItems.value.length > 0) {
      await loadBoxesForImage(verificationItems.value[0])
    }
  } catch (error) {
    handleApiError(error, '加载检测结果失败')
  }
}

async function loadBoxesForImage(item) {
  imageLoaded.value = false
  boxes.value = []
  selectedBoxId.value = null
  hasChanges.value = false
  deletedBoxIds.value.clear()
  selectAll.value = false

  try {
    const params = isCharStage.value
      ? { type: 'char', parentSegmentId: item.id }
      : { sourceImageId: item.id, type: stage.value }

    const segments = await groupsAPI.getGroupSegments(groupId.value, params)

    boxes.value = (segments || []).map((seg) => {
      const canvasBox = toCanvasBox(seg, item)
      return ({
      id: seg.id,
      segmentId: seg.id,
      source_image_id: seg.source_image_id || item.id,
      parent_segment_id: seg.parent_segment_id || (isCharStage.value ? item.id : null),
      x: canvasBox.x,
      y: canvasBox.y,
      width: canvasBox.width,
      height: canvasBox.height,
      verified: true,
      rejected: false,
      selected: false,
      isNew: false,
      isDirty: false
      })
    })

    await loadCanvasImage(item)
  } catch (error) {
    handleApiError(error, '加载检测框失败')
    imageLoaded.value = true
  }
}

function initCanvas() {
  const canvas = canvasRef.value
  const container = canvasContainerRef.value
  if (!canvas || !container) return

  const rect = container.getBoundingClientRect()
  canvasWidth = Math.floor(rect.width) || 800
  canvasHeight = Math.floor(rect.height) || 600
  canvas.width = canvasWidth
  canvas.height = canvasHeight
  ctx = canvas.getContext('2d')

  canvas.addEventListener('mousedown', handleCanvasMouseDown)
  canvas.addEventListener('mousemove', handleCanvasMouseMove)
  canvas.addEventListener('mouseup', handleCanvasMouseUp)
  canvas.addEventListener('mouseleave', handleCanvasMouseUp)
}

async function loadCanvasImage(item) {
  const canvas = canvasRef.value
  const container = canvasContainerRef.value
  if (!canvas || !container || !item) return

  const API_BASE_URL = import.meta.env.VITE_BACKEND_BASE_URL || 'http://127.0.0.1:8000'
  const token = userStore.session?.access_token || ''
  const fileUrl = isCharStage.value
    ? groupsAPI.getSegmentFileUrl(groupId.value, item.id)
    : `${API_BASE_URL}/api/groups/${groupId.value}/images/${item.id}/file`

  try {
    const resp = await fetch(fileUrl, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`)
    }

    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const imgEl = new Image()
    imgEl.crossOrigin = 'anonymous'

    imgEl.onload = () => {
      cachedImageElement = imgEl
      naturalWidth = imgEl.naturalWidth
      naturalHeight = imgEl.naturalHeight

      const rect = container.getBoundingClientRect()
      scale = Math.min(rect.width / naturalWidth, rect.height / naturalHeight, 1)
      canvasWidth = Math.floor(naturalWidth * scale)
      canvasHeight = Math.floor(naturalHeight * scale)
      canvas.width = canvasWidth
      canvas.height = canvasHeight

      ctx = canvas.getContext('2d')
      render()
      imageLoaded.value = true
      URL.revokeObjectURL(url)
    }

    imgEl.onerror = () => {
      drawCanvasError('图像加载失败')
      imageLoaded.value = true
      URL.revokeObjectURL(url)
    }

    imgEl.src = url
  } catch (error) {
    console.error('图像加载失败', error)
    drawCanvasError('图像加载失败')
    imageLoaded.value = true
  }
}

function drawCanvasError(message) {
  const canvas = canvasRef.value
  if (!canvas) return

  ctx = canvas.getContext('2d')
  ctx.fillStyle = '#f5f5f5'
  ctx.fillRect(0, 0, canvasWidth, canvasHeight)
  ctx.fillStyle = '#999'
  ctx.font = '16px sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText(message, canvasWidth / 2, canvasHeight / 2)
}

function render() {
  if (!ctx) return

  ctx.clearRect(0, 0, canvasWidth, canvasHeight)
  ctx.fillStyle = '#f5f5f5'
  ctx.fillRect(0, 0, canvasWidth, canvasHeight)

  if (cachedImageElement) {
    ctx.drawImage(cachedImageElement, 0, 0, canvasWidth, canvasHeight)
  }

  boxes.value.forEach((box, index) => {
    const isSelected = box.id === selectedBoxId.value

    ctx.fillStyle = isSelected ? 'rgba(255, 255, 0, 0.2)' : 'rgba(0, 128, 0, 0.1)'
    ctx.fillRect(box.x * scale, box.y * scale, box.width * scale, box.height * scale)

    ctx.strokeStyle = isSelected ? '#FFD700' : '#00AA00'
    ctx.lineWidth = isSelected ? 3 : 2
    ctx.strokeRect(box.x * scale, box.y * scale, box.width * scale, box.height * scale)

    ctx.fillStyle = isSelected ? '#FFD700' : '#00AA00'
    ctx.font = 'bold 14px sans-serif'
    ctx.fillText(`${index + 1}`, box.x * scale + 5, box.y * scale + 18)

    if (box.verified) {
      ctx.fillStyle = '#67C23A'
      ctx.fillText('✓', box.x * scale + box.width * scale - 20, box.y * scale + 18)
    } else if (box.rejected) {
      ctx.fillStyle = '#F56C6C'
      ctx.fillText('✕', box.x * scale + box.width * scale - 20, box.y * scale + 18)
    }

    if (isSelected) {
      drawResizeHandles(box)
    }
  })

  if (isAddingBox.value && isDragging.value && dragState.value.type === 'create') {
    const { startX, startY, currentX, currentY } = dragState.value
    const x = Math.min(startX, currentX)
    const y = Math.min(startY, currentY)
    const w = Math.abs(currentX - startX)
    const h = Math.abs(currentY - startY)
    ctx.strokeStyle = '#409EFF'
    ctx.lineWidth = 2
    ctx.setLineDash([5, 5])
    ctx.strokeRect(x, y, w, h)
    ctx.setLineDash([])
  }
}

function drawResizeHandles(box) {
  const handleSize = 8
  const x = box.x * scale
  const y = box.y * scale
  const w = box.width * scale
  const h = box.height * scale

  const handles = [
    { name: 'nw', x: x - handleSize / 2, y: y - handleSize / 2 },
    { name: 'ne', x: x + w - handleSize / 2, y: y - handleSize / 2 },
    { name: 'sw', x: x - handleSize / 2, y: y + h - handleSize / 2 },
    { name: 'se', x: x + w - handleSize / 2, y: y + h - handleSize / 2 },
    { name: 'n', x: x + w / 2 - handleSize / 2, y: y - handleSize / 2 },
    { name: 's', x: x + w / 2 - handleSize / 2, y: y + h - handleSize / 2 },
    { name: 'e', x: x + w - handleSize / 2, y: y + h / 2 - handleSize / 2 },
    { name: 'w', x: x - handleSize / 2, y: y + h / 2 - handleSize / 2 }
  ]

  handles.forEach((handle) => {
    ctx.fillStyle = '#FFD700'
    ctx.fillRect(handle.x, handle.y, handleSize, handleSize)
    ctx.strokeStyle = '#333'
    ctx.lineWidth = 1
    ctx.strokeRect(handle.x, handle.y, handleSize, handleSize)
  })
}

function getBoxAtPoint(x, y) {
  for (let i = boxes.value.length - 1; i >= 0; i -= 1) {
    const box = boxes.value[i]
    const bx = box.x * scale
    const by = box.y * scale
    const bw = box.width * scale
    const bh = box.height * scale

    if (x >= bx && x <= bx + bw && y >= by && y <= by + bh) {
      return box
    }
  }
  return null
}

function getResizeHandle(x, y, box) {
  const handleSize = 10
  const bx = box.x * scale
  const by = box.y * scale
  const bw = box.width * scale
  const bh = box.height * scale

  const handles = [
    { name: 'nw', x: bx, y: by },
    { name: 'ne', x: bx + bw, y: by },
    { name: 'sw', x: bx, y: by + bh },
    { name: 'se', x: bx + bw, y: by + bh },
    { name: 'n', x: bx + bw / 2, y: by },
    { name: 's', x: bx + bw / 2, y: by + bh },
    { name: 'e', x: bx + bw, y: by + bh / 2 },
    { name: 'w', x: bx, y: by + bh / 2 }
  ]

  return handles.find((handle) => Math.abs(x - handle.x) <= handleSize && Math.abs(y - handle.y) <= handleSize)?.name || null
}

function handleCanvasMouseDown(event) {
  const rect = canvasRef.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  if (isAddingBox.value) {
    isDragging.value = true
    dragState.value = { startX: x, startY: y, currentX: x, currentY: y, boxId: null, type: 'create', originalBox: null }
    return
  }

  if (selectedBox.value) {
    const handle = getResizeHandle(x, y, selectedBox.value)
    if (handle) {
      isResizing.value = true
      resizeHandle.value = handle
      dragState.value = {
        startX: x,
        startY: y,
        currentX: x,
        currentY: y,
        boxId: selectedBox.value.id,
        type: 'resize',
        originalBox: { ...selectedBox.value }
      }
      return
    }
  }

  const clickedBox = getBoxAtPoint(x, y)
  if (clickedBox) {
    selectedBoxId.value = clickedBox.id
    isDragging.value = true
    dragState.value = {
      startX: x,
      startY: y,
      currentX: x,
      currentY: y,
      boxId: clickedBox.id,
      type: 'move',
      originalBox: { ...clickedBox }
    }
    render()
  } else {
    selectedBoxId.value = null
    render()
  }
}

function handleCanvasMouseMove(event) {
  if (!isDragging.value && !isResizing.value) return

  const rect = canvasRef.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  if (isAddingBox.value && isDragging.value && dragState.value.type === 'create') {
    dragState.value.currentX = x
    dragState.value.currentY = y
    render()
    return
  }

  if (isResizing.value && resizeHandle.value) {
    const original = dragState.value.originalBox
    const dx = (x - dragState.value.startX) / scale
    const dy = (y - dragState.value.startY) / scale
    const newBox = { ...original }

    switch (resizeHandle.value) {
      case 'nw':
        newBox.x = original.x + dx
        newBox.y = original.y + dy
        newBox.width = original.width - dx
        newBox.height = original.height - dy
        break
      case 'ne':
        newBox.y = original.y + dy
        newBox.width = original.width + dx
        newBox.height = original.height - dy
        break
      case 'sw':
        newBox.x = original.x + dx
        newBox.width = original.width - dx
        newBox.height = original.height + dy
        break
      case 'se':
        newBox.width = original.width + dx
        newBox.height = original.height + dy
        break
      case 'n':
        newBox.y = original.y + dy
        newBox.height = original.height - dy
        break
      case 's':
        newBox.height = original.height + dy
        break
      case 'e':
        newBox.width = original.width + dx
        break
      case 'w':
        newBox.x = original.x + dx
        newBox.width = original.width - dx
        break
      default:
        break
    }

    if (newBox.width < 20) {
      if (resizeHandle.value.includes('w')) {
        newBox.x = original.x + original.width - 20
      }
      newBox.width = 20
    }
    if (newBox.height < 20) {
      if (resizeHandle.value.includes('n')) {
        newBox.y = original.y + original.height - 20
      }
      newBox.height = 20
    }

    const boxIndex = boxes.value.findIndex((box) => box.id === dragState.value.boxId)
    if (boxIndex !== -1) {
      boxes.value[boxIndex] = { ...boxes.value[boxIndex], ...newBox, isDirty: true }
      hasChanges.value = true
      render()
    }
    return
  }

  if (isDragging.value && dragState.value.type === 'move') {
    const dx = (x - dragState.value.startX) / scale
    const dy = (y - dragState.value.startY) / scale
    const boxIndex = boxes.value.findIndex((box) => box.id === dragState.value.boxId)
    if (boxIndex !== -1) {
      const original = dragState.value.originalBox
      boxes.value[boxIndex] = {
        ...boxes.value[boxIndex],
        x: Math.max(0, original.x + dx),
        y: Math.max(0, original.y + dy),
        isDirty: true
      }
      hasChanges.value = true
      render()
    }
  }
}

function handleCanvasMouseUp() {
  if (isAddingBox.value && isDragging.value && dragState.value.type === 'create') {
    const { startX, startY, currentX, currentY } = dragState.value
    const x = Math.min(startX, currentX)
    const y = Math.min(startY, currentY)
    const w = Math.abs(currentX - startX)
    const h = Math.abs(currentY - startY)

    if (w > 10 && h > 10) {
      const newBox = {
        id: `box_${Date.now()}`,
        segmentId: null,
        source_image_id: isCharStage.value
          ? (currentImage.value?.original_source_image_id || currentImage.value?.source_image_id)
          : currentImage.value?.id,
        parent_segment_id: isCharStage.value ? currentImage.value?.id : null,
        x: x / scale,
        y: y / scale,
        width: w / scale,
        height: h / scale,
        selected: false,
        verified: false,
        rejected: false,
        isNew: true,
        isDirty: false
      }
      boxes.value.push(newBox)
      selectedBoxId.value = newBox.id
      hasChanges.value = true
      isAddingBox.value = false
      ElMessage.success('已添加新框')
    }
  }

  isDragging.value = false
  isResizing.value = false
  resizeHandle.value = null
  dragState.value = {
    startX: 0,
    startY: 0,
    currentX: 0,
    currentY: 0,
    boxId: null,
    type: null,
    originalBox: null
  }
  render()
}

function handleSelectBox(boxId) {
  if (isAddingBox.value) return
  selectedBoxId.value = boxId
  render()
}

function handleBatchSelect(boxId, selected) {
  const boxIndex = boxes.value.findIndex((box) => box.id === boxId)
  if (boxIndex !== -1) {
    boxes.value[boxIndex].selected = selected
  }
  updateSelectAllState()
}

function handleSelectAll(value) {
  boxes.value.forEach((box) => {
    box.selected = value
  })
}

function updateSelectAllState() {
  const selected = boxes.value.filter((box) => box.selected).length
  selectAll.value = selected === boxes.value.length && boxes.value.length > 0
}

function handleAddNewBox() {
  selectedBoxId.value = null
  isAddingBox.value = true
  ElMessage.info('在画布上拖动绘制新框')
}

function handleBatchDelete() {
  const selectedBoxes = boxes.value.filter((box) => box.selected)
  if (selectedBoxes.length === 0) {
    ElMessage.warning('请先选择要删除的框')
    return
  }

  ElMessageBox.confirm(`确定要删除选中的 ${selectedBoxes.length} 个框吗？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    const selectedIds = new Set(selectedBoxes.map((box) => box.id))
    selectedBoxes.forEach((box) => {
      if (!box.isNew && box.segmentId) {
        deletedBoxIds.value.add(box.segmentId)
      }
    })
    boxes.value = boxes.value.filter((box) => !selectedIds.has(box.id))
    if (selectedBoxId.value && selectedIds.has(selectedBoxId.value)) {
      selectedBoxId.value = null
    }
    hasChanges.value = true
    ElMessage.success('已删除选中的框')
    render()
  }).catch(() => {})
}

function handleZoom(newScale) {
  scale = newScale
  render()
}

function handleFitCanvas() {
  if (!naturalWidth || !naturalHeight || !canvasContainerRef.value) return
  const rect = canvasContainerRef.value.getBoundingClientRect()
  scale = Math.min(rect.width / naturalWidth, rect.height / naturalHeight, 1)
  render()
}

async function handleConfirm() {
  try {
    const segmentIdsToValidate = []

    if (deletedBoxIds.value.size > 0) {
      const idsToDelete = Array.from(deletedBoxIds.value)
      for (const segmentId of idsToDelete) {
        try {
          await groupsAPI.deleteSegment(groupId.value, segmentId)
        } catch (error) {
          console.warn('删除片段失败:', segmentId, error)
        }
      }
      deletedBoxIds.value.clear()
    }

    for (const box of boxes.value) {
      const persistedBox = toPersistedBox(box)
      if (box.isNew) {
        const created = await groupsAPI.createSegment(groupId.value, {
          source_image_id: box.source_image_id,
          segment_type: stage.value,
          bbox_x: persistedBox.bbox_x,
          bbox_y: persistedBox.bbox_y,
          bbox_width: persistedBox.bbox_width,
          bbox_height: persistedBox.bbox_height,
          parent_segment_id: box.parent_segment_id || null,
          validated: true
        })
        if (created?.id) {
          box.id = created.id
          box.segmentId = created.id
          box.isNew = false
          segmentIdsToValidate.push(created.id)
        }
      } else if (box.isDirty) {
        await groupsAPI.updateSegment(groupId.value, box.segmentId, {
          bbox_x: persistedBox.bbox_x,
          bbox_y: persistedBox.bbox_y,
          bbox_width: persistedBox.bbox_width,
          bbox_height: persistedBox.bbox_height,
          validated: true
        })
        if (box.segmentId) {
          segmentIdsToValidate.push(box.segmentId)
        }
      } else if (box.segmentId) {
        segmentIdsToValidate.push(box.segmentId)
      }
    }

    if (isCharStage.value) {
      await groupsAPI.validateSegments(groupId.value, { segment_ids: segmentIdsToValidate })
    } else {
      await groupsAPI.validateSegments(groupId.value, { image_id: currentImage.value?.id })
    }

    try {
      await groupsAPI.recropValidatedSegments(
        groupId.value,
        isCharStage.value
          ? (currentImage.value?.original_source_image_id || currentImage.value?.source_image_id)
          : currentImage.value?.id,
        stage.value
      )
    } catch (recropErr) {
      console.warn('重裁剪失败（不影响校验结果）:', recropErr)
    }

    boxes.value.forEach((box) => {
      box.isDirty = false
      box.verified = true
    })
    hasChanges.value = false
    ElMessage.success('校验完成')

    if (stage.value === 'slip') {
      router.push({ path: '/batch-segmentation', query: { groupId: groupId.value, slipVerified: '1' } })
    } else {
      router.push({ path: '/detail', query: { groupId: groupId.value } })
    }
  } catch (error) {
    handleApiError(error, '提交校验结果失败')
  }
}

function handleBack() {
  ElMessageBox.confirm('确定要返回吗？未保存的更改将丢失。', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    router.back()
  }).catch(() => {})
}

async function handlePrevImage() {
  if (currentImageIndex.value <= 0) {
    ElMessage.warning('已经是第一项')
    return
  }
  currentImageIndex.value -= 1
  await loadBoxesForImage(verificationItems.value[currentImageIndex.value])
}

async function handleNextImage() {
  if (currentImageIndex.value >= verificationItems.value.length - 1) {
    ElMessage.warning('已经是最后一项')
    return
  }
  currentImageIndex.value += 1
  await loadBoxesForImage(verificationItems.value[currentImageIndex.value])
}

watch(() => canvasContainerRef.value, () => {
  initCanvas()
})
</script>

<style scoped lang="scss">
.batch-verify-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f0e8;
  padding: 20px;
}

.verify-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: white;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);

  .header-left {
    display: flex;
    align-items: center;
    gap: 15px;
  }

  .header-title {
    font-size: 18px;
    font-weight: 600;
    color: #333;
  }

  .group-name,
  .verify-count,
  .position-indicator {
    font-size: 14px;
    color: #666;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 15px;
  }
}

.verify-content {
  display: grid;
  grid-template-columns: 1fr 350px;
  gap: 20px;
  flex: 1;
  min-height: 0;
}

.canvas-panel,
.thumbnails-panel {
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.canvas-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.canvas-container {
  position: relative;
  flex: 1;
  min-height: 400px;
  background: #f5f5f5;
  border-radius: 8px;
  overflow: hidden;

  canvas {
    display: block;
    cursor: crosshair;
  }
}

.canvas-placeholder {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #999;
}

.canvas-footer {
  margin-top: 12px;
  padding: 10px 12px;
  background: #f5f5f5;
  border-radius: 8px;

  .canvas-hint {
    font-size: 13px;
    color: #666;
  }
}

.thumbnails-header {
  margin-bottom: 16px;

  .image-name {
    display: block;
    font-size: 16px;
    font-weight: 600;
    color: #333;
    margin-bottom: 8px;
  }

  .detection-info {
    font-size: 13px;
    color: #666;
  }
}

.thumbnails-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  flex: 1;
  overflow-y: auto;
  margin-bottom: 16px;
}

.thumbnail-item {
  position: relative;
  aspect-ratio: 1;
  background: #f5f5f5;
  border: 2px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;

  &:hover {
    border-color: #409eff;
  }

  &--selected {
    border-color: #ffd700;
    background: rgba(255, 215, 0, 0.1);
  }

  &--verified {
    border-color: #67c23a;
  }

  &--rejected {
    border-color: #f56c6c;
  }

  .thumbnail-index {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: #409eff;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 700;
  }

  .thumbnail-status {
    position: absolute;
    top: 4px;
    right: 4px;
  }

  .thumbnail-checkbox {
    position: absolute;
    bottom: 4px;
    left: 4px;
  }
}

.thumbnails-actions {
  display: flex;
  gap: 12px;

  .el-button {
    flex: 1;
  }
}

.thumbnails-footer {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #eee;
}
</style>
