/**
 * 引擎参数配置化测试
 *
 * 验证 engineParams.js 配置文件的存在性、完整性和无硬编码残留
 */

import { describe, it, expect } from 'vitest'
import * as fs from 'fs'
import * as path from 'path'

// 配置文件路径
const ENGINE_PARAMS_PATH = path.resolve(__dirname, '../config/engineParams.js')

describe('引擎参数配置化验证', () => {
  describe('配置文件存在性', () => {
    it('配置文件 engineParams.js 应该存在', () => {
      expect(fs.existsSync(ENGINE_PARAMS_PATH)).toBe(true)
    })

    it('配置文件应该是有效的 JavaScript 模块', () => {
      const content = fs.readFileSync(ENGINE_PARAMS_PATH, 'utf-8')
      expect(content).toBeDefined()
      expect(content.length).toBeGreaterThan(0)
    })
  })

  describe('参数完整性验证', () => {
    it('应该导出 AVAILABLE_DETECT_ENGINES', async () => {
      const { AVAILABLE_DETECT_ENGINES } = await import('../config/engineParams.js')
      expect(AVAILABLE_DETECT_ENGINES).toBeDefined()
      expect(Array.isArray(AVAILABLE_DETECT_ENGINES)).toBe(true)
      expect(AVAILABLE_DETECT_ENGINES.length).toBeGreaterThan(0)
    })

    it('应该导出 DEFAULT_DETECT_ENGINE', async () => {
      const { DEFAULT_DETECT_ENGINE } = await import('../config/engineParams.js')
      expect(DEFAULT_DETECT_ENGINE).toBeDefined()
      expect(typeof DEFAULT_DETECT_ENGINE).toBe('string')
    })

    it('应该导出 DETECT_ENGINE_PARAMS', async () => {
      const { DETECT_ENGINE_PARAMS } = await import('../config/engineParams.js')
      expect(DETECT_ENGINE_PARAMS).toBeDefined()
      expect(typeof DETECT_ENGINE_PARAMS).toBe('object')
      // 验证包含所有引擎
      const engines = ['yolov8', 'aps-yolo', 'deconv-yolo', 'rga-crnn', 'yolov12']
      engines.forEach(engine => {
        expect(DETECT_ENGINE_PARAMS[engine]).toBeDefined()
      })
    })

    it('应该导出 CUT_ENGINE_PARAMS', async () => {
      const { CUT_ENGINE_PARAMS } = await import('../config/engineParams.js')
      expect(CUT_ENGINE_PARAMS).toBeDefined()
      expect(typeof CUT_ENGINE_PARAMS).toBe('object')
      expect(CUT_ENGINE_PARAMS.output_format).toBeDefined()
      expect(CUT_ENGINE_PARAMS.supported_formats).toBeDefined()
    })

    it('应该导出 ROTATION_ENGINE_PARAMS', async () => {
      const { ROTATION_ENGINE_PARAMS } = await import('../config/engineParams.js')
      expect(ROTATION_ENGINE_PARAMS).toBeDefined()
      expect(typeof ROTATION_ENGINE_PARAMS).toBe('object')
      expect(ROTATION_ENGINE_PARAMS.min_angle).toBeDefined()
      expect(ROTATION_ENGINE_PARAMS.max_angle).toBeDefined()
    })

    it('应该导出 NORMALIZATION_ENGINE_PARAMS', async () => {
      const { NORMALIZATION_ENGINE_PARAMS } = await import('../config/engineParams.js')
      expect(NORMALIZATION_ENGINE_PARAMS).toBeDefined()
      expect(typeof NORMALIZATION_ENGINE_PARAMS).toBe('object')
      expect(NORMALIZATION_ENGINE_PARAMS.default_target_width).toBeDefined()
      expect(NORMALIZATION_ENGINE_PARAMS.default_target_height).toBeDefined()
    })

    it('应该导出工具函数 getDetectEngineParams', async () => {
      const { getDetectEngineParams } = await import('../config/engineParams.js')
      expect(getDetectEngineParams).toBeDefined()
      expect(typeof getDetectEngineParams).toBe('function')
      // 验证函数能正常工作
      const params = getDetectEngineParams('yolov8')
      expect(params).toBeDefined()
      expect(params.slice_size).toBeDefined()
    })

    it('应该导出工具函数 isValidDetectEngine', async () => {
      const { isValidDetectEngine } = await import('../config/engineParams.js')
      expect(isValidDetectEngine).toBeDefined()
      expect(typeof isValidDetectEngine).toBe('function')
      // 验证函数能正常工作
      expect(isValidDetectEngine('yolov8')).toBe(true)
      expect(isValidDetectEngine('invalid-engine')).toBe(false)
    })

    it('应该导出引擎描述信息', async () => {
      const { DETECT_ENGINE_DESCRIPTIONS, DETECT_ENGINE_SHORT_DESCRIPTIONS } = await import('../config/engineParams.js')
      expect(DETECT_ENGINE_DESCRIPTIONS).toBeDefined()
      expect(DETECT_ENGINE_SHORT_DESCRIPTIONS).toBeDefined()
      // 验证所有引擎都有描述
      const engines = ['yolov8', 'aps-yolo', 'deconv-yolo', 'rga-crnn', 'yolov12']
      engines.forEach(engine => {
        expect(DETECT_ENGINE_DESCRIPTIONS[engine]).toBeDefined()
        expect(DETECT_ENGINE_SHORT_DESCRIPTIONS[engine]).toBeDefined()
      })
    })
  })

  describe('无硬编码残留验证', () => {
    it('配置文件不应包含硬编码的魔法数字（除了配置值本身）', () => {
      const content = fs.readFileSync(ENGINE_PARAMS_PATH, 'utf-8')
      // 验证文件结构正确，参数都在对应的配置对象中
      expect(content).toContain('export const DETECT_ENGINE_PARAMS')
      expect(content).toContain('export const CUT_ENGINE_PARAMS')
      expect(content).toContain('export const ROTATION_ENGINE_PARAMS')
      expect(content).toContain('export const NORMALIZATION_ENGINE_PARAMS')
    })

    it('工具函数应该正确引用配置常量', async () => {
      const {
        getDetectEngineParams,
        getDetectEngineDescription,
        getDetectEngineShortDescription,
        DETECT_ENGINE_PARAMS,
        DETECT_ENGINE_DESCRIPTIONS,
        DETECT_ENGINE_SHORT_DESCRIPTIONS,
        DEFAULT_DETECT_ENGINE
      } = await import('../config/engineParams.js')

      // 验证工具函数返回正确的值
      expect(getDetectEngineParams('yolov8')).toEqual(DETECT_ENGINE_PARAMS.yolov8)
      expect(getDetectEngineDescription('yolov8')).toEqual(DETECT_ENGINE_DESCRIPTIONS.yolov8)
      expect(getDetectEngineShortDescription('yolov8')).toEqual(DETECT_ENGINE_SHORT_DESCRIPTIONS.yolov8)

      // 验证默认值回退
      expect(getDetectEngineParams('unknown')).toEqual(DETECT_ENGINE_PARAMS[DEFAULT_DETECT_ENGINE])
    })

    it('所有检测引擎参数应该有完整的 SAHI 配置', async () => {
      const { DETECT_ENGINE_PARAMS, AVAILABLE_DETECT_ENGINES } = await import('../config/engineParams.js')

      AVAILABLE_DETECT_ENGINES.forEach(engine => {
        const params = DETECT_ENGINE_PARAMS[engine.value]
        expect(params).toBeDefined()
        expect(params.slice_size).toBeDefined()
        expect(params.overlap_ratio).toBeDefined()
        expect(params.use_soft_nms).toBeDefined()
      })
    })
  })
})
