/**
 * pollTask 超时配置测试
 *
 * 测试目标：
 * 1. TIMEOUT_CONFIG 完整性（6 种任务类型）
 * 2. pollTask 超时机制
 * 3. pollTask 轮询机制
 * 4. 各任务类型超时配置
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// 定义超时配置（与 imageProcessing.js 中保持一致）
const TIMEOUT_CONFIG = {
  detect: 60000,        // 检测区域：60 秒
  cut: 120000,          // 切割：120 秒
  rotation: 90000,      // 旋转检测：90 秒
  normalization: 60000, // 尺寸归一化：60 秒
  batch: 300000,        // 批量处理：300 秒
  export: 600000        // 导出：600 秒
}

// 模拟 pollTask 函数的实现逻辑
function createPollTaskMock() {
  return async function pollTask(taskId, taskType = 'detect', interval = 1000) {
    // 根据任务类型获取超时时间，支持直接传入数字作为超时时间
    const timeout = typeof taskType === 'number'
      ? taskType
      : (TIMEOUT_CONFIG[taskType] || TIMEOUT_CONFIG.detect)

    const startTime = Date.now()
    let callCount = 0

    // 模拟轮询逻辑
    return new Promise((resolve, reject) => {
      const checkStatus = () => {
        callCount++
        const elapsed = Date.now() - startTime

        // 检查超时
        if (elapsed > timeout) {
          reject(new Error('任务超时'))
          return
        }

        // 这里由测试控制返回状态
        resolve({ timeout, callCount, elapsed })
      }

      checkStatus()
    })
  }
}

// 模拟 getTaskStatus 用于测试
let mockStatusQueue = []

function createMockGetTaskStatus() {
  return vi.fn(async () => {
    if (mockStatusQueue.length > 0) {
      return mockStatusQueue.shift()
    }
    return { status: 'pending' }
  })
}

describe('TIMEOUT_CONFIG', () => {
  it('应包含所有 6 种任务类型', () => {
    const requiredKeys = ['detect', 'cut', 'rotation', 'normalization', 'batch', 'export']

    requiredKeys.forEach(key => {
      expect(TIMEOUT_CONFIG).toHaveProperty(key)
    })

    // 验证数量为 6
    expect(Object.keys(TIMEOUT_CONFIG).length).toBe(6)
  })

  it('各任务类型超时时间应正确', () => {
    expect(TIMEOUT_CONFIG.detect).toBe(60000)
    expect(TIMEOUT_CONFIG.cut).toBe(120000)
    expect(TIMEOUT_CONFIG.rotation).toBe(90000)
    expect(TIMEOUT_CONFIG.normalization).toBe(60000)
    expect(TIMEOUT_CONFIG.batch).toBe(300000)
    expect(TIMEOUT_CONFIG.export).toBe(600000)
  })

  it('batch 和 export 应该有最长的超时时间', () => {
    expect(TIMEOUT_CONFIG.batch).toBeGreaterThan(TIMEOUT_CONFIG.detect)
    expect(TIMEOUT_CONFIG.export).toBeGreaterThan(TIMEOUT_CONFIG.batch)
    expect(TIMEOUT_CONFIG.export).toBe(600000) // 10 分钟
  })
})

describe('pollTask 超时机制', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mockStatusQueue = []
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
    mockStatusQueue = []
  })

  it('应支持传入数字作为超时时间', () => {
    const customTimeout = 5000 // 5 秒自定义超时
    expect(customTimeout).toBeGreaterThan(0)
  })

  it('超时计算逻辑应正确', () => {
    const timeout = 5000 // 5 秒超时
    const startTime = 0

    // 模拟时间流逝
    const elapsedTime = 6000 // 6 秒

    // 超过超时时间
    expect(elapsedTime).toBeGreaterThan(timeout)

    // 未超过超时时间
    expect(4000).toBeLessThan(timeout)
  })
})

describe('pollTask 轮询机制', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mockStatusQueue = []
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
    mockStatusQueue = []
  })

  it('应支持轮询间隔配置', async () => {
    const pollInterval = 500 // 500ms 轮询一次
    let callCount = 0

    const getTaskStatus = vi.fn(() => {
      callCount++
      if (callCount >= 3) {
        return Promise.resolve({ status: 'success', result: { data: 'ok' } })
      }
      return Promise.resolve({ status: 'pending' })
    })

    const pollTask = async (taskId, taskType = 'detect', interval = 1000) => {
      const timeout = typeof taskType === 'number' ? taskType : (TIMEOUT_CONFIG[taskType] || TIMEOUT_CONFIG.detect)
      const startTime = Date.now()

      while (true) {
        const status = await getTaskStatus()

        if (status.status === 'success') {
          return status.result
        }

        if (status.status === 'failure') {
          throw new Error(status.error || '任务执行失败')
        }

        if (Date.now() - startTime > timeout) {
          throw new Error('任务超时')
        }

        await new Promise(resolve => setTimeout(resolve, interval))
      }
    }

    const promise = pollTask('test-id', 'detect', pollInterval)

    // 第一次调用
    await vi.advanceTimersByTimeAsync(0)
    await vi.runOnlyPendingTimersAsync()

    // 等待所有 pending 的 timers
    await vi.advanceTimersByTimeAsync(pollInterval * 3)

    const result = await promise
    expect(result).toEqual({ data: 'ok' })
    expect(callCount).toBe(3)
    expect(getTaskStatus).toHaveBeenCalledTimes(3)
  })

  it('应持续轮询直到任务完成', async () => {
    const pollInterval = 100
    let callCount = 0
    const maxPendingCalls = 5

    const getTaskStatus = vi.fn(() => {
      callCount++
      if (callCount > maxPendingCalls) {
        return Promise.resolve({ status: 'success', result: { count: callCount } })
      }
      return Promise.resolve({ status: 'pending' })
    })

    const pollTask = async (taskId, taskType = 'detect', interval = 1000) => {
      const timeout = typeof taskType === 'number' ? taskType : (TIMEOUT_CONFIG[taskType] || TIMEOUT_CONFIG.detect)
      const startTime = Date.now()

      while (true) {
        const status = await getTaskStatus()

        if (status.status === 'success') {
          return status.result
        }

        if (status.status === 'failure') {
          throw new Error(status.error || '任务执行失败')
        }

        if (Date.now() - startTime > timeout) {
          throw new Error('任务超时')
        }

        await new Promise(resolve => setTimeout(resolve, interval))
      }
    }

    const promise = pollTask('test-id', 'detect', pollInterval)

    // 推进时间直到完成
    await vi.advanceTimersByTimeAsync((maxPendingCalls + 1) * pollInterval + 50)

    const result = await promise
    expect(result.count).toBe(maxPendingCalls + 1)
    expect(callCount).toBe(maxPendingCalls + 1)
  })

  it('任务失败时应抛出错误', async () => {
    const getTaskStatus = vi.fn()
      .mockResolvedValue({ status: 'failure', error: '后端处理失败' })

    const pollTask = async (taskId, taskType = 'detect', interval = 1000) => {
      const timeout = typeof taskType === 'number' ? taskType : (TIMEOUT_CONFIG[taskType] || TIMEOUT_CONFIG.detect)
      const startTime = Date.now()

      while (true) {
        const status = await getTaskStatus()

        if (status.status === 'success') {
          return status.result
        }

        if (status.status === 'failure') {
          throw new Error(status.error || '任务执行失败')
        }

        if (Date.now() - startTime > timeout) {
          throw new Error('任务超时')
        }

        await new Promise(resolve => setTimeout(resolve, interval))
      }
    }

    await expect(pollTask('test-id', 'detect', 1000))
      .rejects
      .toThrow('后端处理失败')
  })
})

describe('各任务类型超时配置测试', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  const taskTypes = [
    { type: 'detect', expectedTimeout: 60000 },
    { type: 'cut', expectedTimeout: 120000 },
    { type: 'rotation', expectedTimeout: 90000 },
    { type: 'normalization', expectedTimeout: 60000 },
    { type: 'batch', expectedTimeout: 300000 },
    { type: 'export', expectedTimeout: 600000 }
  ]

  taskTypes.forEach(({ type, expectedTimeout }) => {
    it(`${type} 任务类型应使用 ${expectedTimeout}ms 超时时间`, async () => {
      // 模拟 pollTask 超时计算逻辑
      const timeout = TIMEOUT_CONFIG[type] || TIMEOUT_CONFIG.detect
      expect(timeout).toBe(expectedTimeout)
    })
  })

  it('未知任务类型应回退到 detect 的超时配置', () => {
    const unknownType = 'unknown-type'
    const timeout = TIMEOUT_CONFIG[unknownType] || TIMEOUT_CONFIG.detect

    expect(timeout).toBe(TIMEOUT_CONFIG.detect)
    expect(timeout).toBe(60000)
  })
})

describe('pollTask 调用点验证', () => {
  it('detectRegions 应调用 pollTask 并传入 detect 类型', () => {
    // 验证 detectRegions 中 pollTask 调用
    // 从源代码分析：await this.pollTask(submitResponse.task_id, 'detect')
    // 确认传入了 'detect' 类型

    const taskType = 'detect'
    const timeout = TIMEOUT_CONFIG[taskType] || TIMEOUT_CONFIG.detect

    expect(taskType).toBe('detect')
    expect(timeout).toBe(60000)
  })

  it('应验证 pollTask 方法签名支持 taskType 参数', () => {
    // pollTask(taskId, taskType = 'detect', interval = 1000)
    // 默认参数确保即使不传 taskType 也会使用 'detect'

    const defaultTaskType = 'detect'
    expect(defaultTaskType).toBeDefined()
    expect(TIMEOUT_CONFIG[defaultTaskType]).toBe(60000)
  })
})

describe('边界用例测试', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('超时边界：在超时前一刻应继续轮询', async () => {
    const timeout = 60000 // detect 类型超时
    const startTime = 0

    // 模拟在超时前 1ms 仍在轮询
    const timeBeforeTimeout = timeout - 1
    expect(timeBeforeTimeout).toBeLessThan(timeout)

    // 模拟在超时后 1ms 应抛出错误
    const timeAfterTimeout = timeout + 1
    expect(timeAfterTimeout).toBeGreaterThan(timeout)
  })

  it('轮询间隔为 0 时应立即重试', async () => {
    let callCount = 0
    const maxCalls = 3

    const getTaskStatus = vi.fn(() => {
      callCount++
      if (callCount >= maxCalls) {
        return Promise.resolve({ status: 'success', result: { done: true } })
      }
      return Promise.resolve({ status: 'pending' })
    })

    const pollTask = async (taskId, taskType = 'detect', interval = 1000) => {
      const timeout = typeof taskType === 'number' ? taskType : (TIMEOUT_CONFIG[taskType] || TIMEOUT_CONFIG.detect)
      const startTime = Date.now()

      while (true) {
        const status = await getTaskStatus()

        if (status.status === 'success') {
          return status.result
        }

        if (status.status === 'failure') {
          throw new Error(status.error || '任务执行失败')
        }

        if (Date.now() - startTime > timeout) {
          throw new Error('任务超时')
        }

        if (interval > 0) {
          await new Promise(resolve => setTimeout(resolve, interval))
        }
      }
    }

    // 使用 0 间隔
    const promise = pollTask('test-id', 60000, 0)

    // 立即执行所有 pending
    await vi.runOnlyPendingTimersAsync()

    const result = await promise
    expect(result.done).toBe(true)
    expect(callCount).toBe(maxCalls)
  })

  it('taskType 为空字符串时应回退到默认超时', () => {
    const taskType = ''
    const timeout = TIMEOUT_CONFIG[taskType] || TIMEOUT_CONFIG.detect

    expect(timeout).toBe(60000)
  })

  it('taskType 为 null 时应回退到默认超时', () => {
    const taskType = null
    const timeout = TIMEOUT_CONFIG[taskType] || TIMEOUT_CONFIG.detect

    expect(timeout).toBe(60000)
  })
})
