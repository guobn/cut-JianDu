/**
 * Tests for ImageProcessing Pinia store - activeEngine feature
 */
import { setActivePinia, createPinia } from 'pinia'
import { createApp } from 'vue'
import { useImageProcessingStore } from '../imageProcessing'

describe('ImageProcessing Store - activeEngine', () => {
  let store

  beforeEach(() => {
    const app = createApp({})
    const pinia = createPinia()
    app.use(pinia)
    setActivePinia(pinia)
    store = useImageProcessingStore()
  })

  describe('initial state', () => {
    it('should initialize activeEngine to yolov8', () => {
      expect(store.activeEngine).toBe('yolov8')
    })

    it('should initialize availableEngines with all model types', () => {
      expect(store.availableEngines).toEqual([
        { value: 'yolov8', label: 'YOLOv8 (Baseline)' },
        { value: 'aps-yolo', label: 'APS-YOLO (Small Objects)' },
        { value: 'deconv-yolo', label: 'DeConv-YOLO (Deformable)' },
        { value: 'rga-crnn', label: 'RGA-CRNN (Character Recognition)' }
      ])
    })

    it('should have engineParams computational property', () => {
      expect(store.engineParams).toBeDefined()
    })
  })

  describe('setActiveEngine action', () => {
    it('should update activeEngine', () => {
      store.setActiveEngine('aps-yolo')
      expect(store.activeEngine).toBe('aps-yolo')
    })

    it('should throw error for invalid engine', () => {
      expect(() => store.setActiveEngine('invalid-engine'))
        .toThrow('Invalid detection engine')
    })

    it('should accept all valid engine types', () => {
      const validEngines = ['yolov8', 'aps-yolo', 'deconv-yolo', 'rga-crnn']

      validEngines.forEach(engine => {
        store.setActiveEngine(engine)
        expect(store.activeEngine).toBe(engine)
      })
    })
  })

  describe('getEngineParams action', () => {
    it('should return YOLOv8 specific parameters', () => {
      const params = store.getEngineParams('yolov8')
      expect(params).toEqual({
        slice_size: 640,
        overlap_ratio: 0.25,
        use_soft_nms: true
      })
    })

    it('should return APS-YOLO specific parameters (higher overlap)', () => {
      const params = store.getEngineParams('aps-yolo')
      expect(params).toEqual({
        slice_size: 640,
        overlap_ratio: 0.4,
        use_soft_nms: true
      })
    })

    it('should return DeConv-YOLO parameters', () => {
      const params = store.getEngineParams('deconv-yolo')
      expect(params).toEqual({
        slice_size: 640,
        overlap_ratio: 0.25,
        use_soft_nms: true
      })
    })

    it('should return RGA-CRNN parameters (smaller slice for characters)', () => {
      const params = store.getEngineParams('rga-crnn')
      expect(params).toEqual({
        slice_size: 512,
        overlap_ratio: 0.35,
        use_soft_nms: true
      })
    })

    it('should return default params for unknown engine', () => {
      const params = store.getEngineParams('unknown')
      // Should default to YOLOv8 params
      expect(params).toEqual({
        slice_size: 640,
        overlap_ratio: 0.25,
        use_soft_nms: true
      })
    })
  })

  describe('getCurrentEngineParams computed', () => {
    it('should return params for current activeEngine', () => {
      expect(store.activeEngine).toBe('yolov8')
      const params = store.getCurrentEngineParams
      expect(params).toEqual({
        slice_size: 640,
        overlap_ratio: 0.25,
        use_soft_nms: true
      })
    })

    it('should update when activeEngine changes', () => {
      store.setActiveEngine('aps-yolo')
      expect(store.getCurrentEngineParams).toEqual({
        slice_size: 640,
        overlap_ratio: 0.4,
        use_soft_nms: true
      })
    })
  })
})
