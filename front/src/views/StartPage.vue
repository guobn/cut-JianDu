<template>
  <div class="start-page">
    <div class="start-page__inner">
      <div class="start-page__top-actions start-page__top-actions--left">
        <el-button class="ping-btn" size="small" :loading="meLoading" @click="authMe">鉴权测试</el-button>
      </div>

      <div class="start-page__top-actions start-page__top-actions--right">
        <el-button class="ping-btn" size="small" :loading="pingLoading" @click="pingBackend">后端连通性测试</el-button>
      </div>

      <header class="start-page__header">
        <div class="start-page__title">基于云存储的简牍图片切割及管理系统的设计与实现</div>
        <div class="start-page__subtitle">Ancient Script Analysis System</div>
      </header>

      <section class="start-page__entries">
        <el-row :gutter="18" justify="center">
          <el-col :xs="24" :sm="12" :md="8">
            <el-card class="entry-card" shadow="hover" @click="go('/recognition')">
              <div class="entry-card__content">
                <el-icon class="entry-card__icon" :size="26"><EditPen /></el-icon>
                <div class="entry-card__title">文字识别与标注</div>
                <div class="entry-card__desc">对字符区域进行识别、标注与释读整理。</div>
              </div>
            </el-card>
          </el-col>

          <el-col :xs="24" :sm="12" :md="8">
            <el-card class="entry-card" shadow="hover" @click="go('/metadata')">
              <div class="entry-card__content">
                <el-icon class="entry-card__icon" :size="26"><Files /></el-icon>
                <div class="entry-card__title">图像元数据管理</div>
                <div class="entry-card__desc">管理图像来源、编号、年代与相关字段。</div>
              </div>
            </el-card>
          </el-col>

          <el-col :xs="24" :sm="12" :md="8">
            <el-card class="entry-card" shadow="hover" @click="go('/detail')">
              <div class="entry-card__content">
                <el-icon class="entry-card__icon" :size="26"><View /></el-icon>
                <div class="entry-card__title">简牍图像详情浏览</div>
                <div class="entry-card__desc">查看单张图像的细节、标注与相关信息。</div>
              </div>
            </el-card>
          </el-col>

          <el-col :xs="24" :sm="12" :md="8">
            <el-card class="entry-card" shadow="hover" @click="go('/segmentation')">
              <div class="entry-card__content">
                <el-icon class="entry-card__icon" :size="26"><Scissor /></el-icon>
                <div class="entry-card__title">图像切割工作台</div>
                <div class="entry-card__desc">对简牍图像进行单支检测、单字切割等处理。</div>
              </div>
            </el-card>
          </el-col>

          </el-row>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { handleApiError } from '@/utils/errorHandler'
import { useRouter } from 'vue-router'
import { EditPen, Files, View, Scissor } from '@element-plus/icons-vue'

import request from '@/utils/request'
import { supabase } from '@/lib/supabase'

const router = useRouter()

const go = (path) => {
  router.push(path)
}

const pingLoading = ref(false)
const meLoading = ref(false)

const getBackendBaseUrl = () => {
  const base = import.meta.env.VITE_BACKEND_BASE_URL || 'http://127.0.0.1:8000'
  return String(base).replace(/\/$/, '')
}

const pingBackend = async () => {
  if (pingLoading.value) return
  pingLoading.value = true

  const base = getBackendBaseUrl()
  const url = `${base}/api/ping`

  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), 6000)

  try {
    const res = await fetch(url, { method: 'GET', signal: controller.signal })
    if (!res.ok) {
      throw new Error(`Ping failed: ${res.status}`)
    }
    const data = await res.json()
    if (data?.ok) {
      ElMessage.success(`后端可用：${data?.message ?? 'pong'}`)
    } else {
      ElMessage.warning('后端返回异常（非 ok）')
    }
  } catch (e) {
    const msg = e?.name === 'AbortError' ? '请求超时（6s）' : (e?.message || '请求失败')
    handleApiError(e, '后端不可用')
  } finally {
    window.clearTimeout(timer)
    pingLoading.value = false
  }
}

const authMe = async () => {
  if (meLoading.value) return
  meLoading.value = true
  try {
    const { data } = await supabase.auth.getSession()
    const token = data.session?.access_token
    if (!token) {
      ElMessage.warning('当前未获取到登录 Token（可能未登录/邮箱未验证/会话未恢复），请先登录后再测试。')
      return
    }

    const res = await request.get('/api/me', {
      headers: { Authorization: `Bearer ${token}` }
    })
    const msg = res?.data?.message || '鉴权成功'
    const email = res?.data?.user?.email
    const role = res?.data?.user?.role
    ElMessage.success(email ? `${msg}：${email}${role ? ` (${role})` : ''}` : msg)
  } catch (e) {
    const status = e?.response?.status
    const message = e?.response?.data?.message || e?.message || '请求失败'
    if (status === 401) {
      handleApiError(e, '鉴权失败 (401)：后端未通过校验。请在浏览器 Network 中确认请求头是否包含 Authorization: Bearer <token>。')
      return
    }
    handleApiError(e, status ? `鉴权失败 (${status})` : '鉴权失败')
  } finally {
    meLoading.value = false
  }
}
</script>

<style scoped>
.start-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 42px 16px;
  background: linear-gradient(180deg, #f3f1ea 0%, #f6f7f8 55%, #f5f7fa 100%);
}

.start-page__inner {
  width: 100%;
  max-width: 1020px;
  position: relative;
}

.start-page__top-actions {
  position: absolute;
  top: 0;
  z-index: 2;
}

.start-page__top-actions--left {
  left: 0;
}

.start-page__top-actions--right {
  right: 0;
}

:deep(.ping-btn.el-button) {
  height: 36px;
  padding: 0 18px;
  border-radius: 10px;
  background: #bff2d8;
  border: 1px solid #9be7c0;
  color: #4f7f68;
  font-weight: 600;
  box-shadow: 0 6px 14px rgba(31, 45, 61, 0.08);
  transition: background-color var(--transition-fast), transform var(--transition-fast);
}

:deep(.ping-btn.el-button:hover) {
  background: #b4eed1;
  border-color: #8fe0b6;
  color: #457760;
  transform: translateY(-1px);
}

:deep(.ping-btn.el-button:active) {
  background: #a7e8c8;
  border-color: #84d9ac;
  color: #3c6e58;
}

:deep(.ping-btn.el-button.is-loading),
:deep(.ping-btn.el-button.is-disabled),
:deep(.ping-btn.el-button:disabled) {
  background: #bff2d8;
  border-color: #9be7c0;
  color: rgba(79, 127, 104, 0.75);
  opacity: 0.95;
  transform: none;
}

.start-page__header {
  text-align: center;
  margin-bottom: 26px;
}

.start-page__title {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #2a2f36;
  line-height: 1.3;
}

.start-page__subtitle {
  margin-top: 8px;
  font-size: 14px;
  color: #6b7280;
  letter-spacing: 0.6px;
}

.start-page__entries {
  margin: 0 auto;
}

.start-page__auth {
  margin-top: 18px;
}

.entry-card {
  border-radius: 12px;
  cursor: pointer;
  transition: transform var(--transition-base), box-shadow var(--transition-base);
  border: 1px solid rgba(31, 45, 61, 0.08);
  height: 100%;
}

.entry-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.entry-card:active {
  transform: translateY(-2px);
}

.entry-card__content {
  padding: 6px 2px;
  min-height: 132px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.entry-card__icon {
  color: #2b4b6f;
}

.entry-card__title {
  margin-top: 10px;
  font-size: 15px;
  font-weight: 600;
  color: #1f2d3d;
}

.entry-card__desc {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.6;
  color: #6b7280;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .start-page {
    padding: 32px 12px;
  }

  .start-page__title {
    font-size: 20px;
  }

  .start-page__subtitle {
    font-size: 13px;
  }

  .entry-card__content {
    min-height: 120px;
  }
}

@media (max-width: 576px) {
  .start-page {
    padding: 24px 8px;
  }

  .start-page__title {
    font-size: 18px;
  }

  :deep(.ping-btn.el-button) {
    height: 32px;
    padding: 0 12px;
    font-size: 13px;
  }

  .start-page__top-actions--left,
  .start-page__top-actions--right {
    position: static;
  }

  .start-page__top-actions {
    display: flex;
    justify-content: center;
    gap: 8px;
    margin-bottom: 16px;
  }
}
</style>
