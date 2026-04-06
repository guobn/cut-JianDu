import { fabric } from 'fabric'

/**
 * Canvas 辅助类
 * 封装 Fabric.js 的常用操作
 */

/**
 * 计算两个边界框的 IoU（交并比）
 * @param {Object} box1 - 边界框 1 {x, y, width, height}
 * @param {Object} box2 - 边界框 2 {x, y, width, height}
 * @returns {number} IoU 值 (0-1)
 */
function calculateIoU(box1, box2) {
  const x1_1 = box1.x
  const y1_1 = box1.y
  const x2_1 = box1.x + box1.width
  const y2_1 = box1.y + box1.height

  const x1_2 = box2.x
  const y1_2 = box2.y
  const x2_2 = box2.x + box2.width
  const y2_2 = box2.y + box2.height

  // 计算交集
  const xx1 = Math.max(x1_1, x1_2)
  const yy1 = Math.max(y1_1, y1_2)
  const xx2 = Math.min(x2_1, x2_2)
  const yy2 = Math.min(y2_1, y2_2)

  const interW = Math.max(0, xx2 - xx1)
  const interH = Math.max(0, yy2 - yy1)
  const interArea = interW * interH

  // 计算并集
  const area1 = box1.width * box1.height
  const area2 = box2.width * box2.height
  const unionArea = area1 + area2 - interArea

  // 计算 IoU
  if (unionArea === 0) return 0.0

  return interArea / unionArea
}

/**
 * 过滤重叠的边界框（基于 IoU）
 * 算法：按置信度降序排序，保留高置信度的框，过滤掉与它 IoU > 阈值的低置信度框
 * @param {Array} boxes - 边界框数组
 * @param {number} iouThreshold - IoU 阈值，超过此值视为重叠（默认 0.85 即 85% 重叠）
 * @param {number} minConfidence - 最小置信度，低于此值的框直接过滤
 * @returns {Array} 过滤后的边界框数组
 */
export function filterOverlappingBoxes(boxes, iouThreshold = 0.85, minConfidence = 0.2) {
  if (!boxes || boxes.length <= 1) {
    return boxes
  }

  // 按置信度降序排序
  const sortedBoxes = [...boxes].sort((a, b) => {
    const confA = a.confidence || 0
    const confB = b.confidence || 0
    return confB - confA
  })

  const keep = []
  const used = new Set()

  for (let i = 0; i < sortedBoxes.length; i++) {
    if (used.has(i)) continue

    const box = sortedBoxes[i]

    // 过滤低置信度的框
    if (box.confidence < minConfidence) {
      used.add(i)
      continue
    }

    // 保留当前框
    keep.push(box)
    used.add(i)

    // 标记与当前框高重叠的框
    for (let j = i + 1; j < sortedBoxes.length; j++) {
      if (used.has(j)) continue

      const other = sortedBoxes[j]
      const iou = calculateIoU(box, other)

      // 如果 IoU 超过阈值，过滤掉这个框（因为它的置信度较低）
      if (iou > iouThreshold) {
        used.add(j)
      }
    }
  }

  // 按原始 order 排序返回
  return keep.sort((a, b) => (a.order || 0) - (b.order || 0))
}

export class CanvasHelper {
  constructor(canvasElement, options = {}) {
    // 1. 强制取整，防止 CSS 挤压导致的小数点宽度
    const width = Math.floor(options.width || 800)
    const height = Math.floor(options.height || 500)

    // 2. 初始化 Fabric 实例
    this.canvas = new fabric.Canvas(canvasElement, {
      width: width,
      height: height,
      backgroundColor: options.backgroundColor || '#f5f5f5',
      // 关键：关闭高分屏缩放，确保 1:1 坐标系，解决 1036.79 这种像素偏移
      enableRetinaScaling: false,
      selection: true,
      preserveObjectStacking: true
    })

    this.backgroundImage = null
    this.boundingBoxes = []
    this.boxIdCounter = 0
    this.onBoxesChanged = null

    this.isDrawingBox = false
    this._drawingBox = null
    this._drawingStartPoint = null
    this._drawingHandlers = null

    // 设置默认样式
    this.defaultBoxStyle = {
      fill: 'rgba(64, 158, 255, 0.1)',
      stroke: '#409EFF',
      strokeWidth: 2,
      cornerColor: '#409EFF',
      cornerSize: 8,
      transparentCorners: false,
      cornerStyle: 'circle',
      borderColor: '#409EFF',
      borderScaleFactor: 2
    }

    this._setupEventListeners()
  }

  _getImageTransform() {
    const scale = this.backgroundImage ? this.backgroundImage.scaleX : 1
    const imgLeft = this.backgroundImage
      ? this.backgroundImage.left - (this.backgroundImage.width * scale) / 2
      : 0
    const imgTop = this.backgroundImage
      ? this.backgroundImage.top - (this.backgroundImage.height * scale) / 2
      : 0
    return { scale, imgLeft, imgTop }
  }

  _emitBoxesChanged() {
    if (typeof this.onBoxesChanged === 'function') {
      this.onBoxesChanged(this.getBoundingBoxes())
    }
  }

  /**
   * 设置事件监听器
   */
  _setupEventListeners() {
    // 对象修改事件
    this.canvas.on('object:modified', (e) => {
      this._onObjectModified(e)
    })

    // 对象选中事件
    this.canvas.on('selection:created', (e) => {
      this._onSelectionCreated(e)
    })

    // 对象取消选中事件
    this.canvas.on('selection:cleared', (e) => {
      this._onSelectionCleared(e)
    })
  }

  /**
   * 标准图像加载方法 (官方推荐模式)
   */
  async loadImage(imageUrl) {
    return new Promise((resolve, reject) => {
      // 彻底清空当前画布
      this.canvas.clear()
      this.boundingBoxes = []
      this.canvas.setBackgroundColor('#f5f5f5', this.canvas.renderAll.bind(this.canvas))

      fabric.Image.fromURL(
        imageUrl,
        (img) => {
          if (!img) {
            return reject(new Error('Fabric 无法解析图片对象，请检查图片链接或 CORS 设置'))
          }

          const canvasW = this.canvas.getWidth()
          const canvasH = this.canvas.getHeight()

          // 计算适配比例：图片长边适配画布，并保留 5% 的留白
          const scale = Math.min(
            (canvasW * 0.95) / img.width,
            (canvasH * 0.95) / img.height,
            1 // 限制最大缩放为原图大小
          )

          // 设置图片属性
          img.set({
            originX: 'center',
            originY: 'center',
            left: canvasW / 2,
            top: canvasH / 2,
            scaleX: scale,
            scaleY: scale,
            selectable: false, // 作为背景不可选择
            evented: false, // 不响应鼠标事件
            strokeWidth: 0
          })

          this.backgroundImage = img
          this.canvas.add(img)
          this.canvas.sendToBack(img)

          // 使用官方推荐的异步渲染方法
          this.canvas.requestRenderAll()

          console.log('图片加载完成，当前画布对象数:', this.canvas.getObjects().length)
          resolve(img)
        },
        { crossOrigin: 'anonymous' }
      ) // 必须开启跨域声明
    })
  }

  /**
   * 添加边界框
   * @param {Object} bbox - 边界框数据 {id, x, y, width, height, order}
   * @returns {fabric.Rect} 创建的矩形对象
   */
  addBoundingBox(bbox) {
    const { scale, imgLeft, imgTop } = this._getImageTransform()
    const x = Number(bbox.x) || 0
    const y = Number(bbox.y) || 0
    const w = Number(bbox.width) || 1
    const h = Number(bbox.height) || 1

    const rect = new fabric.Rect({
      width: w * scale,
      height: h * scale,
      left: 0,
      top: 0,
      originX: 'left',
      originY: 'top',
      ...this.defaultBoxStyle,
      data: {
        id: bbox.id,
        order: bbox.order ?? 0,
        originalX: x,
        originalY: y,
        originalWidth: w,
        originalHeight: h
      }
    })

    const text = new fabric.Text(String(bbox.order ?? 0), {
      left: 5,
      top: 5,
      originX: 'left',
      originY: 'top',
      fontSize: 14,
      fill: '#409EFF',
      fontWeight: 'bold',
      selectable: false,
      evented: false
    })

    const group = new fabric.Group([rect, text], {
      left: imgLeft + x * scale,
      top: imgTop + y * scale,
      originX: 'left',
      originY: 'top',
      data: {
        id: bbox.id,
        order: bbox.order ?? 0,
        type: 'boundingBox'
      }
    })

    this.canvas.add(group)
    this.boundingBoxes.push(group)
    this.canvas.requestRenderAll()
    this._emitBoxesChanged()

    return group
  }

  /**
   * 批量添加边界框（自动过滤重叠框）
   * @param {Array} bboxes - 边界框数组
   */
  addBoundingBoxes(bboxes) {
    if (!Array.isArray(bboxes) || bboxes.length === 0) return

    // 不进行任何过滤，直接显示所有检测框
    console.info('[addBoundingBoxes] 原始框数=%d, 显示所有框（无过滤）', bboxes.length)

    bboxes.forEach((bbox) => {
      this.addBoundingBox(bbox)
    })
    this.boundingBoxes.forEach((g) => g.setCoords && g.setCoords())
    this.canvas.requestRenderAll()
  }

  startDrawingBoundingBox(bbox) {
    if (!this.backgroundImage) {
      throw new Error('请先加载图像')
    }

    if (this.isDrawingBox) {
      return
    }

    this.isDrawingBox = true
    this.setSelectionEnabled(false)

    const onMouseDown = (opt) => {
      const p0 = this.canvas.getPointer(opt.e)
      // 不再对起始点做任何裁剪，直接使用当前坐标
      const startX = p0.x
      const startY = p0.y
      this._drawingStartPoint = { x: startX, y: startY }

      const rect = new fabric.Rect({
        width: 1,
        height: 1,
        left: 0,
        top: 0,
        originX: 'left',
        originY: 'top',
        ...this.defaultBoxStyle,
        data: {
          id: bbox.id,
          order: bbox.order,
          originalX: 0,
          originalY: 0,
          originalWidth: 1,
          originalHeight: 1
        }
      })

      const text = new fabric.Text(String(bbox.order), {
        left: 5,
        top: 5,
        originX: 'left',
        originY: 'top',
        fontSize: 14,
        fill: '#409EFF',
        fontWeight: 'bold',
        selectable: false,
        evented: false
      })

      const group = new fabric.Group([rect, text], {
        left: startX,
        top: startY,
        originX: 'left',
        originY: 'top',
        data: {
          id: bbox.id,
          order: bbox.order,
          type: 'boundingBox'
        }
      })

      this._drawingBox = group
      this.canvas.add(group)
      this.boundingBoxes.push(group)
      this.canvas.requestRenderAll()
    }

    const onMouseMove = (opt) => {
      if (!this._drawingBox || !this._drawingStartPoint) return

      const p1 = this.canvas.getPointer(opt.e)
      const x = p1.x
      const y = p1.y

      const start = this._drawingStartPoint
      const left = Math.min(start.x, x)
      const top = Math.min(start.y, y)
      const width = Math.abs(x - start.x)
      const height = Math.abs(y - start.y)

      this._drawingBox.set({ left, top })
      const rect = this._drawingBox.getObjects()[0]
      rect.set({ width: Math.max(1, width), height: Math.max(1, height) })
      this._drawingBox.setCoords()
      this.canvas.requestRenderAll()
    }

    const onMouseUp = () => {
      if (!this._drawingBox) {
        this.stopDrawingBoundingBox()
        return
      }

      const bboxRect = this._drawingBox.getBoundingRect(true, true)
      if (bboxRect.width < 5 || bboxRect.height < 5) {
        this.canvas.remove(this._drawingBox)
        this.boundingBoxes = this.boundingBoxes.filter((b) => b !== this._drawingBox)
      }

      this.stopDrawingBoundingBox()
      this.updateBoxOrders()
      this._emitBoxesChanged()
    }

    this._drawingHandlers = { onMouseDown, onMouseMove, onMouseUp }
    this.canvas.on('mouse:down', onMouseDown)
    this.canvas.on('mouse:move', onMouseMove)
    this.canvas.on('mouse:up', onMouseUp)
  }

  stopDrawingBoundingBox() {
    if (this._drawingHandlers) {
      this.canvas.off('mouse:down', this._drawingHandlers.onMouseDown)
      this.canvas.off('mouse:move', this._drawingHandlers.onMouseMove)
      this.canvas.off('mouse:up', this._drawingHandlers.onMouseUp)
    }

    this._drawingHandlers = null
    this.isDrawingBox = false
    this._drawingBox = null
    this._drawingStartPoint = null
    this.setSelectionEnabled(true)
  }

  /**
   * 删除边界框
   * @param {string} id - 边界框ID
   */
  removeBoundingBox(id) {
    const box = this.boundingBoxes.find((b) => b.data.id === id)
    if (box) {
      this.canvas.remove(box)
      this.boundingBoxes = this.boundingBoxes.filter((b) => b.data.id !== id)
      this.canvas.requestRenderAll()
      this._emitBoxesChanged()
    }
  }

  /**
   * 删除选中的边界框
   */
  removeSelectedBoxes() {
    const activeObjects = this.canvas.getActiveObjects()
    activeObjects.forEach((obj) => {
      if (obj.data && obj.data.type === 'boundingBox') {
        this.removeBoundingBox(obj.data.id)
      }
    })
    this.canvas.discardActiveObject()
    this.canvas.requestRenderAll()
    this._emitBoxesChanged()
  }

  /**
   * 清空所有边界框
   */
  clearBoundingBoxes() {
    this.boundingBoxes.forEach((box) => {
      this.canvas.remove(box)
    })
    this.boundingBoxes = []
    this.canvas.requestRenderAll()
    this._emitBoxesChanged()
  }

  /**
   * 获取所有边界框数据
   * @returns {Array} 边界框数组
   */
  getBoundingBoxes() {
    const { scale, imgLeft, imgTop } = this._getImageTransform()

    return this.boundingBoxes.map((box, index) => {
      const rect = box.getObjects()[0] // 获取矩形对象

      const bboxRect = box.getBoundingRect(true, true)

      return {
        id: box.data.id,
        x: Math.round((bboxRect.left - imgLeft) / scale),
        y: Math.round((bboxRect.top - imgTop) / scale),
        width: Math.round(bboxRect.width / scale),
        height: Math.round(bboxRect.height / scale),
        confidence: 1.0,
        rotation: 0.0,
        order: index + 1
      }
    })
  }

  /**
   * 更新边界框序号
   */
  updateBoxOrders() {
    this.boundingBoxes.forEach((box, index) => {
      box.data.order = index + 1
      const text = box.getObjects()[1] // 获取文本对象
      if (text) {
        text.set('text', String(index + 1))
      }
    })
    this.canvas.requestRenderAll()
    this._emitBoxesChanged()
  }

  /**
   * 清空画布
   */
  clear() {
    this.canvas.clear()
    this.backgroundImage = null
    this.boundingBoxes = []
    this._emitBoxesChanged()
  }

  /**
   * 设置画布大小
   * @param {number} width - 宽度
   * @param {number} height - 高度
   */
  setSize(width, height) {
    this.canvas.setWidth(width)
    this.canvas.setHeight(height)
    this.canvas.requestRenderAll()
  }

  /**
   * 缩放画布功能
   */
  zoom(ratio) {
    const zoom = this.canvas.getZoom() * ratio
    this.canvas.setZoom(Math.min(Math.max(zoom, 0.1), 10)) // 限制缩放范围
    this.canvas.requestRenderAll()
  }

  /**
   * 适应画布
   */
  fitToCanvas() {
    if (this.backgroundImage) {
      this.canvas.setZoom(1)
      this.canvas.absolutePan({ x: 0, y: 0 })
      this.canvas.requestRenderAll()
    }
  }

  /**
   * 启用/禁用选择
   * @param {boolean} enabled - 是否启用
   */
  setSelectionEnabled(enabled) {
    this.canvas.selection = enabled
    this.boundingBoxes.forEach((box) => {
      box.set('selectable', enabled)
      box.set('evented', enabled)
    })
    this.canvas.requestRenderAll()
  }

  /**
   * 导出为图像
   * @param {string} format - 格式 ('png', 'jpeg')
   * @returns {string} Data URL
   */
  toDataURL(format = 'png') {
    return this.canvas.toDataURL({
      format: format,
      quality: 1
    })
  }

  /**
   * 销毁画布
   */
  dispose() {
    if (this.canvas) {
      this.canvas.dispose()
    }
  }

  // 事件处理器

  _onObjectModified(e) {
    // 对象修改后的处理
    console.log('Object modified:', e.target)
    if (e.target?.data?.type === 'boundingBox') {
      this._emitBoxesChanged()
    }
  }

  _onSelectionCreated(e) {
    // 对象选中后的处理
    console.log('Selection created:', e.selected)
  }

  _onSelectionCleared(e) {
    // 对象取消选中后的处理
    console.log('Selection cleared')
  }
}

export default CanvasHelper
