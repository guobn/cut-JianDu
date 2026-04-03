<template>
  <div class="batch-verify-page">
    <!-- Header -->
    <div class="verify-header">
      <div class="header-left">
        <el-button :icon="ArrowLeft" @click="handleBack">返回</el-button>
        <span class="header-title">批量切割 - 单支校验</span>
      </div>
      <div class="header-center">
        <span class="group-name">组名: {{ groupName }}</span>
      </div>
      <div class="header-right">
        <span class="verify-count">已校验: {{ verifiedCount }}/{{ totalCount }}</span>
        <el-button type="primary" :disabled="!hasChanges" @click="handleConfirm">
          确认提交
        </el-button>
      </div>
    </div>

    <!-- Main Content -->
    <div class="verify-content">
      <!-- Left: Canvas -->
      <div class="canvas-panel">
        <div class="canvas-header">
          <span>原图+检测框叠加显示</span>
          <div class="canvas-tools">
            <el-button-group size="small">
              <el-button @click="handleZoom(0.5)" :disabled="!imageLoaded">50%</el-button>
              <el-button @click="handleZoom(0.75)" :disabled="!imageLoaded">75%</el-button>
              <el-button type="primary" @click="handleZoom(1)" :disabled="!imageLoaded">100%</el-button>
              <el-button @click="handleFitCanvas" :disabled="!imageLoaded">适应</el-button>
            </el-button-group>
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
            <span v-else-if="selectedBox">已选中框 #{{ selectedBoxIndex + 1 }}，拖动调整位置/大小</span>
            <span v-else>点击选中框，黄色边框高亮显示</span>
          </div>
        </div>
      </div>

      <!-- Right: Thumbnails -->
      <div class="thumbnails-panel">
        <div class="thumbnails-header">
          <span class="image-name">{{ currentImageName }}</span>
          <span class="detection-info">检测到: {{ totalCount }}根 已校验: {{ verifiedCount }}/{{ totalCount }}</span>
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
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Check, Close, QuestionFilled, Picture } from '@element-plus/icons-vue'
import { groupsAPI } from '@/api/groups'
import { handleApiError } from '@/utils/errorHandler'

const route = useRoute()
const router = useRouter()

// Refs
const canvasContainerRef = ref(null)
const canvasRef = ref(null)

// State
const groupId = computed(() => route.params.groupId)
const stage = computed(() => route.params.stage) // 'slip' | 'char'

const groupName = ref('')
const currentImageName = ref('')
const imageLoaded = ref(false)
const imageUrl = ref('')

// Canvas state
let ctx = null
let canvasWidth = 800
let canvasHeight = 600
let scale = 1
let imageElement = null

// Boxes: [{id, x, y, width, height, selected, verified, rejected}]
const boxes = ref([])
const selectedBoxId = ref(null)
const isAddingBox = ref(false)
const isDragging = ref(false)
const isResizing = ref(false)
const dragStartPos = ref({ x: 0, y: 0 })
const resizeHandle = ref(null) // 'nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w'

// Batch selection
const selectAll = ref(false)

// Computed
const selectedBox = computed(() => boxes.value.find(b => b.id === selectedBoxId.value))
const selectedBoxIndex = computed(() => boxes.value.findIndex(b => b.id === selectedBoxId.value))
const totalCount = computed(() => boxes.value.length)
const verifiedCount = computed(() => boxes.value.filter(b => b.verified).length)
const hasChanges = computed(() => boxes.value.some(b => b.selected || b.verified || b.rejected))
const hasSelectedBoxes = computed(() => boxes.value.some(b => b.selected))
const isIndeterminate = computed(() => {
  const selected = boxes.value.filter(b => b.selected).length
  return selected > 0 && selected < boxes.value.length
})

// Load data
onMounted(async () => {
  await loadGroupData()
  await loadDetectionResults()
  initCanvas()
})

onBeforeUnmount(() => {
  if (imageElement) {
    imageElement.onload = null
  }
})

async function loadGroupData() {
  try {
    const response = await groupsAPI.getGroup(groupId.value)
    groupName.value = response.data.name
  } catch (error) {
    handleApiError(error, '加载组信息失败')
  }
}

async function loadDetectionResults() {
  // Load mock detection results for now
  // In a real implementation, this would call an API to get detection results
  // For testing, create sample boxes
  try {
    // Simulated detection results - in real app, fetch from API
    const sampleBoxes = [
      { id: 'box_1', x: 100, y: 50, width: 80, height: 300, selected: false, verified: true, rejected: false },
      { id: 'box_2', x: 200, y: 60, width: 75, height: 280, selected: false, verified: true, rejected: false },
      { id: 'box_3', x: 300, y: 55, width: 85, height: 290, selected: false, verified: true, rejected: false },
      { id: 'box_4', x: 400, y: 65, width: 70, height: 270, selected: false, verified: false, rejected: true },
      { id: 'box_5', x: 500, y: 45, width: 90, height: 310, selected: false, verified: false, rejected: false },
      { id: 'box_6', x: 600, y: 70, width: 78, height: 285, selected: false, verified: false, rejected: false },
      { id: 'box_7', x: 700, y: 55, width: 82, height: 295, selected: false, verified: false, rejected: false },
      { id: 'box_8', x: 800, y: 60, width: 76, height: 288, selected: false, verified: false, rejected: false },
    ]
    boxes.value = sampleBoxes
    currentImageName.value = 'IMG_001.png'
    imageUrl.value = '/api/groups/' + groupId.value + '/preview'
  } catch (error) {
    handleApiError(error, '加载检测结果失败')
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

  // Load background image
  loadCanvasImage()

  // Event listeners
  canvas.addEventListener('mousedown', handleCanvasMouseDown)
  canvas.addEventListener('mousemove', handleCanvasMouseMove)
  canvas.addEventListener('mouseup', handleCanvasMouseUp)
  canvas.addEventListener('mouseleave', handleCanvasMouseUp)
}

async function loadCanvasImage() {
  // For demo purposes, create a placeholder image
  // In real app, load actual image from imageUrl
  const canvas = canvasRef.value
  if (!canvas) return

  ctx = canvas.getContext('2d')
  ctx.fillStyle = '#f5f5f5'
  ctx.fillRect(0, 0, canvasWidth, canvasHeight)

  // Draw placeholder text
  ctx.fillStyle = '#999'
  ctx.font = '16px sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText('图像加载区域', canvasWidth / 2, canvasHeight / 2)

  imageLoaded.value = true
  render()
}

function render() {
  if (!ctx) return

  // Clear canvas
  ctx.clearRect(0, 0, canvasWidth, canvasHeight)

  // Draw background
  ctx.fillStyle = '#f5f5f5'
  ctx.fillRect(0, 0, canvasWidth, canvasHeight)

  // Draw image placeholder
  ctx.fillStyle = '#ddd'
  ctx.fillRect(50, 50, canvasWidth - 100, canvasHeight - 100)

  // Draw grid pattern to simulate image
  ctx.strokeStyle = '#eee'
  ctx.lineWidth = 1
  for (let x = 50; x < canvasWidth - 50; x += 20) {
    ctx.beginPath()
    ctx.moveTo(x, 50)
    ctx.lineTo(x, canvasHeight - 50)
    ctx.stroke()
  }
  for (let y = 50; y < canvasHeight - 50; y += 20) {
    ctx.beginPath()
    ctx.moveTo(50, y)
    ctx.lineTo(canvasWidth - 50, y)
    ctx.stroke()
  }

  // Draw boxes
  boxes.value.forEach((box, index) => {
    const isSelected = box.id === selectedBoxId.value

    // Box fill
    ctx.fillStyle = isSelected ? 'rgba(255, 255, 0, 0.2)' : 'rgba(0, 128, 0, 0.1)'
    ctx.fillRect(box.x * scale, box.y * scale, box.width * scale, box.height * scale)

    // Box border
    ctx.strokeStyle = isSelected ? '#FFD700' : '#00AA00'
    ctx.lineWidth = isSelected ? 3 : 2
    ctx.strokeRect(box.x * scale, box.y * scale, box.width * scale, box.height * scale)

    // Box label
    ctx.fillStyle = isSelected ? '#FFD700' : '#00AA00'
    ctx.font = 'bold 14px sans-serif'
    ctx.fillText(`${index + 1}`, box.x * scale + 5, box.y * scale + 18)

    // Status indicator
    if (box.verified) {
      ctx.fillStyle = '#67C23A'
      ctx.fillText('✓', box.x * scale + box.width * scale - 20, box.y * scale + 18)
    } else if (box.rejected) {
      ctx.fillStyle = '#F56C6C'
      ctx.fillText('✗', box.x * scale + box.width * scale - 20, box.y * scale + 18)
    }

    // Draw resize handles if selected
    if (isSelected) {
      drawResizeHandles(box)
    }
  })

  // Draw new box being created
  if (isAddingBox.value && isDragging.value) {
    const { startX, startY, currentX, currentY } = dragState.value || {}
    if (startX !== undefined) {
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
    { name: 'w', x: x - handleSize / 2, y: y + h / 2 - handleSize / 2 },
  ]

  handles.forEach(handle => {
    ctx.fillStyle = '#FFD700'
    ctx.fillRect(handle.x, handle.y, handleSize, handleSize)
    ctx.strokeStyle = '#333'
    ctx.lineWidth = 1
    ctx.strokeRect(handle.x, handle.y, handleSize, handleSize)
  })
}

const dragState = ref({
  startX: 0,
  startY: 0,
  currentX: 0,
  currentY: 0,
  boxId: null,
  type: null // 'move', 'resize', 'create'
})

function handleCanvasMouseDown(e) {
  const rect = canvasRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top

  if (isAddingBox.value) {
    // Start creating new box
    isDragging.value = true
    dragState.value = {
      startX: x,
      startY: y,
      currentX: x,
      currentY: y,
      type: 'create'
    }
    return
  }

  // Check if clicking on resize handle of selected box
  if (selectedBox.value) {
    const handle = getResizeHandle(x, y, selectedBox.value)
    if (handle) {
      isResizing.value = true
      resizeHandle.value = handle
      dragState.value = {
        startX: x,
        startY: y,
        boxId: selectedBox.value.id,
        type: 'resize',
        originalBox: { ...selectedBox.value }
      }
      return
    }
  }

  // Check if clicking on a box
  const clickedBox = getBoxAtPoint(x, y)
  if (clickedBox) {
    selectedBoxId.value = clickedBox.id
    isDragging.value = true
    dragState.value = {
      startX: x,
      startY: y,
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

function handleCanvasMouseMove(e) {
  if (!isDragging.value && !isResizing.value) return

  const rect = canvasRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top

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

    let newBox = { ...original }
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
    }

    // Ensure minimum size
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

    const boxIndex = boxes.value.findIndex(b => b.id === dragState.value.boxId)
    if (boxIndex !== -1) {
      boxes.value[boxIndex] = newBox
      render()
    }
    return
  }

  if (isDragging.value && dragState.value.type === 'move') {
    const dx = (x - dragState.value.startX) / scale
    const dy = (y - dragState.value.startY) / scale

    const boxIndex = boxes.value.findIndex(b => b.id === dragState.value.boxId)
    if (boxIndex !== -1) {
      const original = dragState.value.originalBox
      boxes.value[boxIndex] = {
        ...boxes.value[boxIndex],
        x: Math.max(0, original.x + dx),
        y: Math.max(0, original.y + dy)
      }
      render()
    }
  }
}

function handleCanvasMouseUp(e) {
  if (isAddingBox.value && isDragging.value && dragState.value.type === 'create') {
    const { startX, startY, currentX, currentY } = dragState.value
    const x = Math.min(startX, currentX)
    const y = Math.min(startY, currentY)
    const w = Math.abs(currentX - startX)
    const h = Math.abs(currentY - startY)

    if (w > 10 && h > 10) {
      // Create new box
      const newBox = {
        id: `box_${Date.now()}`,
        x: x / scale,
        y: y / scale,
        width: w / scale,
        height: h / scale,
        selected: false,
        verified: false,
        rejected: false
      }
      boxes.value.push(newBox)
      selectedBoxId.value = newBox.id
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
    type: null
  }
  render()
}

function getBoxAtPoint(x, y) {
  // Check boxes in reverse order (top-most first)
  for (let i = boxes.value.length - 1; i >= 0; i--) {
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
    { name: 'w', x: bx, y: by + bh / 2 },
  ]

  for (const handle of handles) {
    if (Math.abs(x - handle.x) <= handleSize && Math.abs(y - handle.y) <= handleSize) {
      return handle.name
    }
  }
  return null
}

// Event handlers
function handleSelectBox(boxId) {
  if (isAddingBox.value) return
  selectedBoxId.value = boxId
  render()
}

function handleBatchSelect(boxId, selected) {
  const boxIndex = boxes.value.findIndex(b => b.id === boxId)
  if (boxIndex !== -1) {
    boxes.value[boxIndex].selected = selected
  }
  updateSelectAllState()
}

function handleSelectAll(val) {
  boxes.value.forEach(box => {
    box.selected = val
  })
}

function updateSelectAllState() {
  const selected = boxes.value.filter(b => b.selected).length
  selectAll.value = selected === boxes.value.length && boxes.value.length > 0
}

function handleAddNewBox() {
  if (selectedBoxId.value) {
    // Mark current selected box as verified before adding new one
    const boxIndex = boxes.value.findIndex(b => b.id === selectedBoxId.value)
    if (boxIndex !== -1) {
      boxes.value[boxIndex].verified = true
    }
  }
  selectedBoxId.value = null
  isAddingBox.value = true
  ElMessage.info('在画布上拖动绘制新框')
}

function handleBatchDelete() {
  const selectedBoxes = boxes.value.filter(b => b.selected)
  if (selectedBoxes.length === 0) {
    ElMessage.warning('请先选择要删除的框')
    return
  }

  ElMessageBox.confirm(`确定要删除选中的 ${selectedBoxes.length} 个框吗？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    const selectedIds = new Set(selectedBoxes.map(b => b.id))
    boxes.value = boxes.value.filter(b => !selectedIds.has(b.id))
    if (selectedBoxId.value && selectedIds.has(selectedBoxId.value)) {
      selectedBoxId.value = null
    }
    ElMessage.success('已删除选中的框')
    render()
  }).catch(() => {})
}

function handleZoom(newScale) {
  scale = newScale
  render()
}

function handleFitCanvas() {
  scale = 1
  render()
}

async function handleConfirm() {
  try {
    // Submit verified boxes
    const verifiedBoxes = boxes.value.filter(b => b.verified).map(b => ({
      id: b.id,
      x: b.x,
      y: b.y,
      width: b.width,
      height: b.height
    }))

    // In real implementation, call API to save verification results
    ElMessage.success('校验结果已提交')

    // Navigate based on stage
    if (stage.value === 'slip') {
      // After slip verification, proceed to char segmentation
      router.push('/batch-segmentation')
    } else {
      // After char verification, go to metadata
      router.push('/metadata')
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

// Watch for canvas container resize
watch(() => canvasContainerRef.value, () => {
  initCanvas()
})
</script>

<style scoped lang="scss">
.batch-verify-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #F5F0E8;
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

  .header-center {
    .group-name {
      font-size: 14px;
      color: #666;
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 15px;

    .verify-count {
      font-size: 14px;
      color: #666;
    }
  }
}

.verify-content {
  display: grid;
  grid-template-columns: 1fr 350px;
  gap: 20px;
  flex: 1;
  min-height: 0;
}

.canvas-panel {
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);

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
}

.thumbnails-panel {
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);

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
      border-color: #409EFF;
    }

    &--selected {
      border-color: #FFD700;
      background: rgba(255, 215, 0, 0.1);
    }

    &--verified {
      border-color: #67C23A;
    }

    &--rejected {
      border-color: #F56C6C;
    }

    .thumbnail-index {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: #409EFF;
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
}
</style>
