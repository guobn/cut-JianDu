<template>
  <div class="start-page">
    <div class="start-page__inner">
      <section class="launch-section launch-section--formal">
        <header class="launch-section__header">
          <div class="launch-section__badge">正式</div>
          <div class="launch-section__title">基于云存储的简牍图片切割及管理系统（正式）</div>
          <div class="launch-section__subtitle">Ancient Script Analysis System</div>
        </header>

        <section class="launch-section__entries">
          <el-row :gutter="18" justify="center">
            <el-col
              v-for="entry in formalEntries"
              :key="entry.title"
              :xs="24"
              :sm="12"
              :md="6"
            >
              <el-card class="entry-card entry-card--formal" shadow="hover" @click="go(entry.path)">
                <div class="entry-card__content">
                  <el-icon class="entry-card__icon" :size="26"><component :is="entry.icon" /></el-icon>
                  <div class="entry-card__title">{{ entry.title }}</div>
                  <div class="entry-card__desc">{{ entry.desc }}</div>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </section>
      </section>

      <section class="launch-section launch-section--beta">
        <div class="start-page__top-actions start-page__top-actions--left">
          <el-button class="ping-btn" size="small" :loading="meLoading" @click="authMe">鉴权测试</el-button>
        </div>

        <div class="start-page__top-actions start-page__top-actions--right">
          <el-button class="ping-btn" size="small" :loading="pingLoading" @click="pingBackend">后端连通性测试</el-button>
        </div>

        <header class="launch-section__header launch-section__header--beta">
          <div class="launch-section__badge">内测</div>
          <div class="launch-section__title">基于云存储的简牍图片切割及管理系统（内测）</div>
          <div class="launch-section__subtitle">Ancient Script Analysis System</div>
        </header>

        <section class="launch-section__entries">
          <el-row :gutter="18" justify="center">
            <el-col
              v-for="entry in betaEntries"
              :key="entry.title"
              :xs="24"
              :sm="12"
              :md="8"
            >
              <el-card class="entry-card" shadow="hover" @click="go(entry.path)">
                <div class="entry-card__content">
                  <el-icon class="entry-card__icon" :size="26"><component :is="entry.icon" /></el-icon>
                  <div class="entry-card__title">{{ entry.title }}</div>
                  <div class="entry-card__desc">{{ entry.desc }}</div>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </section>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { handleApiError } from '@/utils/errorHandler'
import { useRouter } from 'vue-router'
import { EditPen, Files, View, Scissor, FolderOpened, MagicStick } from '@element-plus/icons-vue'

import request from '@/utils/request'
import { supabase } from '@/lib/supabase'

const router = useRouter()

const formalEntries = [
  {
    title: '图像预处理',
    desc: '进入批量估角、旋转校正与归一化流程。',
    path: '/preprocess',
    icon: MagicStick
  },
  {
    title: '图像组管理',
    desc: '管理图像组、导入图片并维护分组数据。',
    path: '/groups',
    icon: FolderOpened
  },
  {
    title: '批量切割',
    desc: '集中执行单支与单字切割，并跟踪批处理进度。',
    path: '/batch-segmentation',
    icon: Scissor
  },
  {
    title: '简牍图像详情',
    desc: '查看图像树、切割结果与细节信息。',
    path: '/detail',
    icon: View
  }
]

const betaEntries = [
  {
    title: '文字识别与标注',
    desc: '对字符区域进行识别、标注与释读整理。',
    path: '/recognition',
    icon: EditPen
  },
  {
    title: '图像元数据管理',
    desc: '管理图像来源、编号、年代与相关字段。',
    path: '/metadata',
    icon: Files
  },
  {
    title: '简牍图像详情浏览',
    desc: '查看单张图像的细节、标注与相关信息。',
    path: '/detail',
    icon: View
  },
  {
    title: '图像切割工作台',
    desc: '对简牍图像进行单支检测、单字切割等处理。',
    path: '/segmentation',
    icon: Scissor
  }
]

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
      ElMessage.warning('当前未获取到登录 Token，请先登录后再测试。')
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
    if (status === 401) {
      handleApiError(e, '鉴权失败 (401)')
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
  padding: 36px 16px 64px;
  background: linear-gradient(180deg, #f3f1ea 0%, #f6f7f8 55%, #f5f7fa 100%);
}

.start-page__inner {
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
  display: grid;
  gap: 32px;
}

.launch-section {
  position: relative;
  border-radius: 24px;
  padding: 34px 24px 28px;
  border: 1px solid rgba(31, 45, 61, 0.08);
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 18px 42px rgba(17, 24, 39, 0.06);
  backdrop-filter: blur(6px);
}

.launch-section--formal {
  background:
    radial-gradient(1000px 300px at 0% 0%, rgba(37, 99, 235, 0.12) 0%, rgba(37, 99, 235, 0) 58%),
    radial-gradient(800px 320px at 100% 0%, rgba(22, 163, 74, 0.10) 0%, rgba(22, 163, 74, 0) 52%),
    rgba(255, 255, 255, 0.9);
}

.launch-section--beta {
  padding-top: 78px;
}

.launch-section__header {
  text-align: center;
  margin-bottom: 26px;
}

.launch-section__header--beta {
  margin-bottom: 30px;
}

.launch-section__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: #eef6ff;
  color: #2b4b6f;
  border: 1px solid rgba(43, 75, 111, 0.12);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.4px;
}

.launch-section__title {
  margin-top: 14px;
  font-size: 30px;
  font-weight: 800;
  letter-spacing: 0.6px;
  color: #1f2d3d;
  line-height: 1.24;
}

.launch-section__subtitle {
  margin-top: 8px;
  font-size: 15px;
  color: #6b7280;
  letter-spacing: 0.6px;
}

.launch-section__entries {
  margin: 0 auto;
}

.start-page__top-actions {
  position: absolute;
  top: 24px;
  z-index: 2;
}

.start-page__top-actions--left {
  left: 24px;
}

.start-page__top-actions--right {
  right: 24px;
}

:deep(.ping-btn.el-button) {
  height: 38px;
  padding: 0 18px;
  border-radius: 12px;
  background: #bff2d8;
  border: 1px solid #9be7c0;
  color: #4f7f68;
  font-weight: 600;
  box-shadow: 0 6px 14px rgba(31, 45, 61, 0.08);
}

:deep(.ping-btn.el-button:hover) {
  background: #b4eed1;
  border-color: #8fe0b6;
  color: #457760;
  transform: translateY(-1px);
}

:deep(.ping-btn.el-button.is-loading),
:deep(.ping-btn.el-button.is-disabled),
:deep(.ping-btn.el-button:disabled) {
  background: #bff2d8;
  border-color: #9be7c0;
  color: rgba(79, 127, 104, 0.75);
}

.entry-card {
  border-radius: 16px;
  cursor: pointer;
  transition: transform var(--transition-base), box-shadow var(--transition-base);
  border: 1px solid rgba(31, 45, 61, 0.08);
  height: 100%;
}

.entry-card--formal {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(247, 250, 252, 0.98) 100%);
}

.entry-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.entry-card:active {
  transform: translateY(-2px);
}

.entry-card__content {
  padding: 10px 6px;
  min-height: 152px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.entry-card__icon {
  color: #2b4b6f;
}

.entry-card__title {
  margin-top: 12px;
  font-size: 18px;
  font-weight: 700;
  color: #1f2d3d;
}

.entry-card__desc {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.65;
  color: #6b7280;
}

@media (max-width: 900px) {
  .launch-section__title {
    font-size: 24px;
  }
}

@media (max-width: 768px) {
  .start-page {
    padding: 24px 12px 40px;
  }

  .launch-section {
    padding: 24px 16px 20px;
  }

  .launch-section--beta {
    padding-top: 24px;
  }

  .launch-section__title {
    font-size: 20px;
  }

  .launch-section__subtitle {
    font-size: 13px;
  }

  .entry-card__content {
    min-height: 136px;
  }

  .start-page__top-actions {
    position: static;
    display: flex;
    justify-content: center;
    margin-bottom: 12px;
  }

  .start-page__top-actions--left,
  .start-page__top-actions--right {
    left: auto;
    right: auto;
  }
}
</style>
