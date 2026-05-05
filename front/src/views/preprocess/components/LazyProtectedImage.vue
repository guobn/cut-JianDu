<template>
  <div
    class="trigger"
    :class="[`trigger--${variant}`, { 'trigger--disabled': !src }]"
    @click="openPreview"
  >
    <el-icon class="trigger__icon"><ZoomIn /></el-icon>
    <span class="trigger__text">{{ triggerLabel }}</span>
  </div>

  <el-dialog
    v-model="dialogVisible"
    :title="title || '查看图片'"
    width="min(960px, calc(100vw - 32px))"
    destroy-on-close
  >
    <div class="dialog-body">
      <div v-if="loading" class="state-block">正在加载图片...</div>
      <img v-else-if="objectUrl" :src="objectUrl" :alt="title || 'image preview'" class="dialog-image">
      <div v-else class="state-block">图片加载失败</div>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ZoomIn } from '@element-plus/icons-vue'
import { supabase } from '@/lib/supabase'

const props = defineProps({
  src: { type: String, default: '' },
  title: { type: String, default: '' },
  label: { type: String, default: '点击查看' },
  variant: { type: String, default: 'thumb' }
})

const API_BASE_URL = import.meta.env.VITE_BACKEND_BASE_URL || 'http://127.0.0.1:8000'

const dialogVisible = ref(false)
const loading = ref(false)
const objectUrl = ref('')

const triggerLabel = computed(() => (props.src ? props.label : '暂无图片'))

const revokeObjectUrl = () => {
  if (objectUrl.value) {
    URL.revokeObjectURL(objectUrl.value)
    objectUrl.value = ''
  }
}

const resolveUrl = (url) => {
  if (!url) return ''
  return url.startsWith('http') ? url : `${API_BASE_URL}${url}`
}

const loadImage = async () => {
  if (!props.src || loading.value || objectUrl.value) return

  loading.value = true
  try {
    const { data } = await supabase.auth.getSession()
    const token = data.session?.access_token
    const response = await fetch(resolveUrl(props.src), {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    })
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    const blob = await response.blob()
    revokeObjectUrl()
    objectUrl.value = URL.createObjectURL(blob)
  } catch (error) {
    ElMessage.error(error.message || '图片加载失败')
  } finally {
    loading.value = false
  }
}

const openPreview = async () => {
  if (!props.src) return
  dialogVisible.value = true
  await loadImage()
}

onBeforeUnmount(() => {
  revokeObjectUrl()
})
</script>

<style scoped>
.trigger {
  display: grid;
  place-items: center;
  gap: 6px;
  border: 1px dashed #d6c7b4;
  background: #f5ebd3;
  color: #3d2817;
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease;
}

.trigger:hover {
  border-color: #a93226;
  transform: translateY(-1px);
}

.trigger--disabled,
.trigger--disabled:hover {
  cursor: not-allowed;
  color: #907c69;
  border-color: #e7dbc9;
  transform: none;
}

.trigger--thumb {
  width: 60px;
  height: 60px;
  border-radius: 6px;
}

.trigger--panel {
  width: min(100%, 280px);
  min-height: 220px;
  border-radius: 8px;
  padding: 16px;
}

.trigger__icon {
  font-size: 18px;
}

.trigger__text {
  font-size: 12px;
  line-height: 1.2;
  text-align: center;
}

.dialog-body {
  min-height: 320px;
  display: grid;
  place-items: center;
}

.dialog-image {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
}

.state-block {
  color: #6f5a47;
}
</style>
