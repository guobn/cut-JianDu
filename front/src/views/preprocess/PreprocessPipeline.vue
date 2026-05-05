<template>
  <div class="pipeline-page">
    <header class="page-header">
      <div>
        <h1>图像预处理</h1>
        <p>为单支切割前的图像组完成批量估角、旋转校正和尺寸归一化。</p>
      </div>
      <div class="group-switcher">
        <el-select
          v-model="selectedGroupId"
          placeholder="继续已有预处理组"
          clearable
          style="width: 260px"
          @change="handleGroupChange"
        >
          <el-option
            v-for="group in store.groups"
            :key="group.id"
            :label="group.name"
            :value="group.id"
          />
        </el-select>
        <el-button type="primary" @click="showCreateDialog = true">创建新组</el-button>
      </div>
    </header>

    <el-steps :active="store.activeStep" finish-status="success" class="steps-bar">
      <el-step title="创建组" />
      <el-step title="上传图片" />
      <el-step title="批量估角" />
      <el-step title="角度审核" />
      <el-step title="应用旋转" />
      <el-step title="批量归一化" />
      <el-step title="转为正式组" />
    </el-steps>

    <section v-if="!store.currentGroup" class="blank-state">
      <el-empty description="先创建一个预处理组，然后再往里放图片。" />
    </section>

    <template v-else>
      <div class="group-banner">
        <div>
          <h2>{{ store.currentGroup.name }}</h2>
          <p>当前阶段：{{ stageLabel }}</p>
        </div>
        <el-tag>{{ store.currentGroup.total_images || 0 }} 张图片</el-tag>
      </div>

      <section v-if="store.activeStep === 0" class="card-shell">
        <el-result icon="info" title="预处理组已创建" sub-title="下一步把图片传进来，然后开始批量估角。">
          <template #extra>
            <el-button type="primary" @click="store.setActiveStep(1)">去上传图片</el-button>
          </template>
        </el-result>
      </section>

      <UploadStep
        v-else-if="store.activeStep === 1"
        :group-id="store.currentGroup.id"
        @next="startDetect"
      />

      <section v-else-if="store.activeStep === 2" class="card-shell">
        <div class="progress-card">
          <h3>批量估角进行中</h3>
          <p>{{ detectProgressText }}</p>
          <el-alert
            v-if="store.progressError"
            type="error"
            :closable="false"
            :title="store.progressError"
          />
          <el-progress :percentage="Math.round(store.progress.percent || 0)" />
          <div v-if="store.progressError" class="progress-actions">
            <el-button @click="store.setActiveStep(1)">返回上传</el-button>
            <el-button type="primary" @click="startDetect">重新估角</el-button>
          </div>
        </div>
      </section>

      <AngleReviewStep
        v-else-if="store.activeStep === 3"
        :group-id="store.currentGroup.id"
        @apply-rotation="beginRotation"
      />

      <section v-else-if="store.activeStep === 4" class="card-shell">
        <div class="progress-card">
          <h3>正在应用旋转</h3>
          <p>逐张覆写本地文件，完成后会自动进入归一化。</p>
          <el-progress indeterminate :percentage="100" />
        </div>
      </section>

      <NormalizeStep
        v-else-if="store.activeStep === 5"
        :group-id="store.currentGroup.id"
        @done="store.setActiveStep(6)"
      />

      <ConvertStep
        v-else-if="store.activeStep === 6"
        :group-id="store.currentGroup.id"
        @back="store.setActiveStep(5)"
      />
    </template>

    <CreateGroupDialog
      v-model="showCreateDialog"
      :loading="creating"
      @submit="createGroup"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { usePreprocessStore } from '@/store/preprocess'
import AngleReviewStep from './components/AngleReviewStep.vue'
import ConvertStep from './components/ConvertStep.vue'
import CreateGroupDialog from './components/CreateGroupDialog.vue'
import NormalizeStep from './components/NormalizeStep.vue'
import UploadStep from './components/UploadStep.vue'

const store = usePreprocessStore()
const showCreateDialog = ref(false)
const creating = ref(false)
const selectedGroupId = ref('')
const applyingRotation = ref(false)

const stageLabel = computed(() => {
  const status = store.currentGroup?.preprocess_status || 'draft'
  const map = {
    draft: '待上传 / 待估角',
    angle_detected: '待审核',
    rotated: '待归一化',
    normalized: '待转换'
  }
  return map[status] || status
})

const detectProgressText = computed(() => {
  if (store.progressError) return '估角任务没有正常完成，可以返回上一步调整后重试。'
  const { done, total } = store.progress
  return total ? `已处理 ${done} / ${total}` : '正在等待任务开始'
})

const createGroup = async (name) => {
  try {
    creating.value = true
    const group = await store.createGroup(name)
    selectedGroupId.value = group.id
    showCreateDialog.value = false
    ElMessage.success('预处理组已创建')
  } catch (error) {
    ElMessage.error(error.message || '创建失败')
  } finally {
    creating.value = false
  }
}

const handleGroupChange = async (groupId) => {
  if (!groupId) return
  const group = store.groups.find((item) => item.id === groupId)
  if (!group) return
  try {
    await store.hydrateGroup(group)
  } catch (error) {
    ElMessage.error(error.message || '加载失败')
  }
}

const startDetect = async () => {
  try {
    await store.detectAngles(store.currentGroup.id)
    ElMessage.success('已提交估角任务')
  } catch (error) {
    ElMessage.error(error.message || '估角任务提交失败')
  }
}

const beginRotation = async () => {
  if (applyingRotation.value) return
  applyingRotation.value = true
  store.setActiveStep(4)
  try {
    await store.applyRotation(store.currentGroup.id)
    ElMessage.success('旋转已应用')
  } catch (error) {
    store.setActiveStep(3)
    ElMessage.error(error.message || '应用旋转失败')
  } finally {
    applyingRotation.value = false
  }
}

watch(() => store.currentGroup?.id, (groupId) => {
  selectedGroupId.value = groupId || ''
})

onMounted(async () => {
  try {
    await store.fetchGroups()
  } catch (error) {
    ElMessage.error(error.message || '初始化失败')
  }
})

onBeforeUnmount(() => {
  store.stopPolling()
})
</script>

<style scoped>
.pipeline-page {
  display: grid;
  gap: 20px;
  padding: 24px;
  background: #f7f2e8;
  min-height: 100%;
}

.page-header,
.group-banner,
.card-shell {
  background: #fff;
  border: 1px solid #eadfcf;
  border-radius: 8px;
}

.page-header,
.group-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 20px 24px;
}

.page-header h1,
.group-banner h2 {
  margin: 0 0 6px;
  color: #3D2817;
}

.page-header p,
.group-banner p {
  margin: 0;
  color: #2C1810;
}

.group-switcher {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.steps-bar {
  padding: 20px 10px 6px;
  background: #fff;
  border: 1px solid #eadfcf;
  border-radius: 8px;
}

.blank-state,
.card-shell {
  padding: 24px;
}

.progress-card {
  display: grid;
  gap: 12px;
  max-width: 560px;
}

.progress-card h3 {
  margin: 0;
  color: #3D2817;
}

.progress-card p {
  margin: 0;
  color: #2C1810;
}

.progress-actions {
  display: flex;
  gap: 12px;
}

@media (max-width: 900px) {
  .page-header,
  .group-banner {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
