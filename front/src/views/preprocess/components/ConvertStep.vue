<template>
  <section class="convert-shell">
    <div class="convert-card">
      <h2>准备就绪</h2>
      <p>这组图片已经完成预处理，可以转入正式图像组。</p>

      <ul class="summary-list">
        <li>组内图片数量：{{ imageCount }}</li>
        <li>已应用旋转 / 跳过：{{ rotatedCount }} / {{ skippedCount }}</li>
        <li>归一化参数：{{ paramsSummary }}</li>
      </ul>

      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="转换为正式图像组后，将无法回到预处理状态"
      />

      <div class="actions">
        <el-button @click="$emit('back')">返回检查</el-button>
        <el-button type="danger" size="large" :loading="loading" @click="submit">转为正式图像组</el-button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElNotification } from 'element-plus'
import { usePreprocessStore } from '@/store/preprocess'

const props = defineProps({
  groupId: { type: String, required: true }
})

defineEmits(['back'])

const router = useRouter()
const store = usePreprocessStore()
const loading = ref(false)

const imageCount = computed(() => store.images.length)
const skippedCount = computed(() => store.images.filter((item) => item.preprocess_skipped).length)
const rotatedCount = computed(() => Math.max(0, imageCount.value - skippedCount.value))
const paramsSummary = computed(() => {
  const params = store.normalizeParams
  if (!params) return '尚未记录'
  return `${params.target_size}px, ${params.keep_ratio ? '保持比例' : '强制拉伸'}, ${params.interp}, ${params.padding}`
})

const submit = async () => {
  try {
    await ElMessageBox.confirm('确认转换为正式图像组？', '最终确认', {
      type: 'warning'
    })
    loading.value = true
    await store.convert(props.groupId)
    ElNotification({
      title: '转换成功',
      message: '已切换为正式图像组，可以继续后续切割流程。',
      type: 'success'
    })
    router.push({ path: '/detail', query: { groupId: props.groupId } })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.convert-shell {
  min-height: 440px;
  display: grid;
  place-items: center;
}

.convert-card {
  width: min(640px, 100%);
  display: grid;
  gap: 18px;
  padding: 28px;
  background: #fff;
  border: 1px solid #eadfcf;
  border-radius: 8px;
}

.convert-card h2 {
  margin: 0;
  color: #3D2817;
}

.convert-card p {
  margin: 0;
  color: #2C1810;
}

.summary-list {
  margin: 0;
  padding-left: 20px;
  color: #2C1810;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
