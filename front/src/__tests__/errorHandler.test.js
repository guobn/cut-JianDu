/**
 * errorHandler.js 单元测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { handleApiError, handleUploadError, ErrorLevel, showError } from '../utils/errorHandler.js'

// Mock ElMessage
vi.mock('element-plus', () => ({
  ElMessage: {
    info: vi.fn(),
    warning: vi.fn(),
    error: vi.fn(),
    success: vi.fn()
  }
}))

import { ElMessage } from 'element-plus'

describe('errorHandler', () => {
  beforeEach(() => {
    // 清除所有 mock 调用记录
    vi.clearAllMocks()
  })

  describe('handleApiError - 标准 API 错误', () => {
    it('应该正确处理后端返回的标准错误格式', () => {
      const error = {
        response: {
          data: {
            error_code: 'USER_NOT_FOUND',
            error_message: '用户不存在',
            suggested_solution: '请检查用户 ID 是否正确'
          },
          status: 404
        }
      }

      const result = handleApiError(error, '获取用户信息')

      expect(result.code).toBe('USER_NOT_FOUND')
      expect(result.message).toBe('用户不存在')
      expect(result.solution).toBe('请检查用户 ID 是否正确')
      expect(result.level).toBe(ErrorLevel.ERROR)
      expect(result.context).toBe('获取用户信息')
      expect(result.fullMessage).toContain('获取用户信息')
      expect(result.fullMessage).toContain('用户不存在')
      expect(ElMessage.error).toHaveBeenCalledTimes(1)
    })
  })

  describe('handleApiError - 网络错误', () => {
    it('应该正确处理网络错误', () => {
      const error = new Error('Network Error')

      const result = handleApiError(error)

      expect(result.code).toBe('NETWORK_ERROR')
      expect(result.message).toBe('网络连接失败，请检查后端服务是否启动')
      expect(result.solution).toBe('确认后端服务在 http://127.0.0.1:8000 运行')
      expect(result.level).toBe(ErrorLevel.ERROR)
      expect(ElMessage.error).toHaveBeenCalledTimes(1)
    })

    it('应该正确处理 Failed to fetch 错误', () => {
      const error = new Error('Failed to fetch')

      const result = handleApiError(error)

      expect(result.code).toBe('NETWORK_ERROR')
      expect(result.message).toContain('网络连接失败')
      expect(ElMessage.error).toHaveBeenCalledTimes(1)
    })
  })

  describe('handleUploadError - 上传错误', () => {
    it('应该正确处理文件上传错误', () => {
      const error = {
        response: {
          data: {
            error_code: 'UPLOAD_FAILED',
            error_message: '文件上传失败'
          },
          status: 500
        }
      }
      const file = { name: 'test.png' }

      const result = handleUploadError(error, file)

      expect(result.fileName).toBe('test.png')
      expect(result.fullMessage).toContain('上传失败')
      expect(result.fullMessage).toContain('test.png')
      expect(ElMessage.error).toHaveBeenCalledTimes(1)
    })

    it('应该正确处理 413 文件大小超限错误', () => {
      const error = {
        response: {
          data: {
            error_code: '413'
          },
          status: 413
        }
      }
      const file = { name: 'large-image.jpg' }

      handleUploadError(error, file)

      expect(ElMessage.error).toHaveBeenCalledWith(expect.stringContaining('大小超过服务器限制'))
    })

    it('应该正确处理 415 文件格式不支持错误', () => {
      const error = {
        response: {
          data: {
            error_code: '415'
          },
          status: 415
        }
      }
      const file = { name: 'document.pdf' }

      handleUploadError(error, file)

      expect(ElMessage.error).toHaveBeenCalledWith(expect.stringContaining('不支持的文件格式'))
    })
  })

  describe('错误分级展示 (warning/error/info)', () => {
    it('应该展示 warning 级别的错误', () => {
      const error = new Error('timeout')

      const result = handleApiError(error)

      expect(result.level).toBe(ErrorLevel.WARNING)
      expect(ElMessage.warning).toHaveBeenCalledTimes(1)
    })

    it('应该展示 error 级别的错误', () => {
      const error = {
        response: {
          data: {
            error_code: 'SERVER_ERROR'
          },
          status: 500
        }
      }

      const result = handleApiError(error)

      expect(result.level).toBe(ErrorLevel.ERROR)
      expect(ElMessage.error).toHaveBeenCalledTimes(1)
    })

    it('应该支持通过 showError 强制指定错误级别', () => {
      const error = new Error('普通错误信息')

      // 强制指定为 info 级别
      showError(error, '测试上下文', 'info')

      expect(ElMessage.info).toHaveBeenCalledTimes(1)
      expect(ElMessage.info).toHaveBeenCalledWith(expect.stringContaining('普通错误信息'))
    })

    it('应该支持通过 showError 指定 warning 级别', () => {
      const error = new Error('警告信息')

      // 强制指定为 warning 级别
      showError(error, '警告', 'warning')

      expect(ElMessage.warning).toHaveBeenCalledTimes(1)
    })
  })
})
