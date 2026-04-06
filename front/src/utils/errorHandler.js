/**
 * 统一错误处理工具
 * 提供 API 错误处理、上传错误处理、分级错误展示等功能
 */

import { ElMessage } from 'element-plus'

/**
 * 错误级别枚举
 */
export const ErrorLevel = {
  INFO: 'info',
  WARNING: 'warning',
  ERROR: 'error'
}

/**
 * 解析 API 错误信息
 * 支持后端返回的标准错误格式：{ error_code, error_message, suggested_solution }
 * @param {Error|Object} error - 错误对象
 * @returns {Object} 解析后的错误信息 { code, message, solution, level }
 */
function parseApiError(error) {
  // 后端返回的标准错误格式
  if (error?.response?.data) {
    const data = error.response.data
    return {
      code: data.error_code || error.response.status || 'UNKNOWN',
      message: data.error_message || data.message || error.message || '请求失败',
      solution: data.suggested_solution || null,
      level: ErrorLevel.ERROR
    }
  }

  // 直接传入的错误对象包含 error_code
  if (error?.error_code) {
    return {
      code: error.error_code,
      message: error.error_message || error.message || '操作失败',
      solution: error.suggested_solution || null,
      level: ErrorLevel.ERROR
    }
  }

  // 网络错误或未知错误
  const msg = error?.message || '未知错误'

  if (msg.includes('Network Error') || msg.includes('Failed to fetch')) {
    return {
      code: 'NETWORK_ERROR',
      message: '网络连接失败，请检查后端服务是否启动',
      solution: '确认后端服务在 http://127.0.0.1:8000 运行',
      level: ErrorLevel.ERROR
    }
  }

  if (msg.includes('timeout')) {
    return {
      code: 'TIMEOUT',
      message: '请求超时，请稍后重试',
      solution: '检查网络状况或联系管理员',
      level: ErrorLevel.WARNING
    }
  }

  return {
    code: 'UNKNOWN',
    message: msg,
    solution: null,
    level: ErrorLevel.ERROR
  }
}

/**
 * 处理 API 错误
 * 解析后端返回的错误信息并展示
 * @param {Error|Object} error - 错误对象
 * @param {string} context - 错误上下文（可选），用于补充错误信息
 * @returns {Object} 解析后的错误信息
 */
export function handleApiError(error, context = '') {
  const parsed = parseApiError(error)

  // 构建完整的错误消息
  let message = parsed.message

  if (context) {
    message = `${context}：${message}`
  }

  // 如果有建议的解决方案，附加在消息后面
  if (parsed.solution) {
    message = `${message}（${parsed.solution}）`
  }

  // 根据错误级别展示
  if (parsed.level === ErrorLevel.WARNING) {
    ElMessage.warning(message)
  } else if (parsed.level === ErrorLevel.INFO) {
    ElMessage.info(message)
  } else {
    ElMessage.error(message)
  }

  // 返回解析结果供调用方使用
  return {
    ...parsed,
    context,
    fullMessage: message
  }
}

/**
 * 处理上传错误
 * 专门针对文件上传场景的错误处理
 * @param {Error|Object} error - 错误对象
 * @param {File} file - 上传的文件（可选）
 * @returns {Object} 解析后的错误信息
 */
export function handleUploadError(error, file = null) {
  const parsed = parseApiError(error)

  let message = parsed.message
  const fileName = file?.name ? `"${file.name}"` : '文件'

  // 常见的上传错误处理（支持字符串和数字错误码比较）
  if (parsed.code === 413 || parsed.code === '413') {
    message = `${fileName} 文件大小超过服务器限制`
    parsed.solution = '压缩文件或联系管理员调整限制'
  } else if (parsed.code === 415 || parsed.code === '415') {
    message = `${fileName} 不支持的文件格式`
    parsed.solution = '请上传支持的图像格式（JPG、PNG、TIFF、BMP）'
  } else if (error?.message?.includes('format') || error?.message?.includes('格式')) {
    message = `${fileName} 格式不支持`
    parsed.solution = '请上传 JPG、PNG、TIFF 或 BMP 格式的图像'
  } else if (error?.message?.includes('size') || error?.message?.includes('大小') || error?.message?.includes('超过限制')) {
    message = `${fileName} 大小超过限制`
    parsed.solution = '请上传小于 50MB 的图像文件'
  } else {
    // 一般上传错误，使用文件名
    message = `${fileName} ${parsed.message}`
  }

  // 附加上下文
  const fullMessage = `上传失败：${message}`

  ElMessage.error(fullMessage)

  return {
    ...parsed,
    fileName: file?.name,
    fullMessage
  }
}

/**
 * 分级展示错误
 * 根据错误类型和严重程度展示不同级别的消息
 * @param {Error|Object} error - 错误对象
 * @param {string} context - 错误上下文
 * @param {'info'|'warning'|'error'} level - 强制指定错误级别（可选）
 */
export function showError(error, context = '', level = null) {
  const parsed = parseApiError(error)

  let message = parsed.message
  if (context) {
    message = `${context}：${message}`
  }

  // 使用指定的级别或解析的级别
  const displayLevel = level || parsed.level

  if (displayLevel === ErrorLevel.INFO) {
    ElMessage.info(message)
  } else if (displayLevel === ErrorLevel.WARNING) {
    ElMessage.warning(message)
  } else {
    ElMessage.error(message)
  }

  return {
    ...parsed,
    context,
    fullMessage: message
  }
}

/**
 * 处理批量操作错误
 * 针对批量删除、批量更新等场景
 * @param {Error|Object} error - 错误对象
 * @param {string} operation - 操作名称（如'删除'、'更新'）
 * @param {number} totalCount - 总数量
 * @param {number} successCount - 成功数量
 */
export function handleBatchError(error, operation = '操作', totalCount = 0, successCount = 0) {
  const parsed = parseApiError(error)

  let message = parsed.message

  if (successCount > 0) {
    message = `成功${operation}${successCount}个，失败${totalCount - successCount}个：${message}`
  } else {
    message = `${operation}失败：${message}`
  }

  ElMessage.error(message)

  return {
    ...parsed,
    operation,
    totalCount,
    successCount,
    fullMessage: message
  }
}

/**
 * 处理认证相关错误
 * @param {Error|Object} error - 错误对象
 * @returns {Object} 解析后的错误信息
 */
export function handleAuthError(error) {
  const status = error?.response?.status

  if (status === 401) {
    ElMessage.error('登录已过期，请重新登录')
    return {
      code: 'AUTH_EXPIRED',
      message: '登录已过期',
      level: ErrorLevel.ERROR,
      needRedirect: true
    }
  }

  if (status === 403) {
    ElMessage.error('没有权限执行此操作')
    return {
      code: 'FORBIDDEN',
      message: '没有权限',
      level: ErrorLevel.ERROR
    }
  }

  return handleApiError(error, '认证失败')
}

/**
 * 默认导出
 */
export default {
  ErrorLevel,
  handleApiError,
  handleUploadError,
  showError,
  handleBatchError,
  handleAuthError,
  parseApiError
}
