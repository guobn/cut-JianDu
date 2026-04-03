<template>
  <div class="batch-seg-page">
    <el-tabs v-model="activeTab" class="batch-seg-tabs">
      <!-- Tab 1: 单支切割 -->
      <el-tab-pane label="单支切割" name="slip">
        <div class="batch-mode">
          <!-- 左侧：图像组选择器 -->
          <div class="batch-left">
            <h3>选择图像组</h3>
            <el-select
              v-model="selectedGroupId"
              placeholder="选择要处理的图像组"
              clearable
              @change="handleGroupChange"
            >
              <el-option
                v-for="group in availableGroups"
                :key="group.id"
                :label="`${group.name} (${group.total_images} 张)`"
                :value="group.id"
              />
            </el-select>

            <div v-if="selectedGroup" class="group-info">
              <p><strong>组名称：</strong> {{ selectedGroup.name }}</p>
              <p><strong>图片数量：</strong> {{ selectedGroup.total_images }} 张</p>
              <p><strong>已处理：</strong> {{ selectedGroup.processed_images }} 张</p>
              <p><strong>状态：</strong> {{ getStatusLabel(selectedGroup.status) }}</p>
            </div>
          </div>

          <!-- 右侧：操作说明 -->
          <div class="batch-right">
            <div class="tips-section">
              <h4>操作说明</h4>
              <ol>
                <li>从左侧选择要处理的图像组</li>
                <li>确认图像组信息无误后，点击下方「开始切割」按钮</li>
                <li>系统将自动使用默认参数进行检测，无需手动配置</li>
                <li>切割完成后可前往校验视图进行调整</li>
              </ol>
            </div>

            <!-- 开始处理按钮 -->
            <el-button
              type="primary"
              class="start-btn"
              :disabled="!selectedGroupId || processing"
              :loading="processing"
              @click="handleStartSegment('slip')"
            >
              开始单支切割
            </el-button>
          </div>
        </div>

        <!-- 进度显示区域 -->
        <div v-if="processing && currentMode === 'slip'" class="progress-section">
          <h3>处理进度</h3>
          <div class="progress-item">
            <span>总进度</span>
            <el-progress
              :percentage="Math.round((progress.completed / progress.total) * 100)"
              :color="getProgressColor"
            />
            <span>{{ progress.completed }}/{{ progress.total }} 张</span>
            <span v-if="progress.failed > 0" style="color:#F56C6C">失败: {{ progress.failed }}</span>
          </div>
          <div v-if="progress.current_file" class="current-file">
            <p>处理中：{{ progress.current_file }}</p>
          </div>
        </div>

        <!-- 完成提示 -->
        <el-result
          v-if="processComplete && currentMode === 'slip'"
          icon="success"
          title="单支切割完成"
          :sub-title="`已处理 ${progress.completed} 张图像`"
        >
          <template #extra>
            <el-button type="primary" @click="handleProceedToCharSegment">
              继续单字切割
            </el-button>
            <el-button @click="resetBatchMode">继续处理其他组</el-button>
          </template>
        </el-result>
      </el-tab-pane>

      <!-- Tab 2: 单字切割 -->
      <el-tab-pane label="单字切割" name="char">
        <el-alert v-if="!slipSegmentDone" type="warning" title="请先完成单支切割和校验后，再进行单字切割" :closable="false" />
        <div class="batch-mode">
          <!-- 左侧：图像组选择器 -->
          <div class="batch-left">
            <h3>选择图像组</h3>
            <el-select
              v-model="selectedGroupId"
              placeholder="选择要处理的图像组"
              clearable
              @change="handleGroupChange"
            >
              <el-option
                v-for="group in availableGroups"
                :key="group.id"
                :label="`${group.name} (${group.total_images} 张)`"
                :value="group.id"
              />
            </el-select>

            <div v-if="selectedGroup" class="group-info">
              <p><strong>组名称：</strong> {{ selectedGroup.name }}</p>
              <p><strong>图片数量：</strong> {{ selectedGroup.total_images }} 张</p>
              <p><strong>已处理：</strong> {{ selectedGroup.processed_images }} 张</p>
              <p><strong>状态：</strong> {{ getStatusLabel(selectedGroup.status) }}</p>
            </div>
          </div>

          <!-- 右侧：操作说明 -->
          <div class="batch-right">
            <div class="tips-section">
              <h4>操作说明</h4>
              <ol>
                <li>从左侧选择要处理的图像组</li>
                <li>确认图像组信息无误后，点击下方「开始切割」按钮</li>
                <li>系统将自动使用默认参数进行检测，无需手动配置</li>
                <li>切割完成后可前往校验视图进行调整</li>
              </ol>
            </div>

            <!-- 开始处理按钮 -->
            <el-button
              type="primary"
              class="start-btn"
              :disabled="!selectedGroupId || processing || !slipSegmentDone"
              :loading="processing"
              @click="handleStartSegment('char')"
            >
              开始单字切割
            </el-button>
          </div>
        </div>

        <!-- 进度显示区域 -->
        <div v-if="processing && currentMode === 'char'" class="progress-section">
          <h3>处理进度</h3>
          <div class="progress-item">
            <span>总进度</span>
            <el-progress
              :percentage="Math.round((progress.completed / progress.total) * 100)"
              :color="getProgressColor"
            />
            <span>{{ progress.completed }}/{{ progress.total }} 张</span>
            <span v-if="progress.failed > 0" style="color:#F56C6C">失败: {{ progress.failed }}</span>
          </div>
          <div v-if="progress.current_file" class="current-file">
            <p>处理中：{{ progress.current_file }}</p>
          </div>
        </div>

        <!-- 完成提示 -->
        <el-result
          v-if="processComplete && currentMode === 'char'"
          icon="success"
          title="单字切割完成"
          :sub-title="`已处理 ${progress.completed} 张图像`"
        >
          <template #extra>
            <el-button type="primary" @click="handleProcessComplete">
              前往元数据管理
            </el-button>
            <el-button @click="resetBatchMode">继续处理其他组</el-button>
          </template>
        </el-result>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useGroupStore } from '@/store/group'
import { groupsAPI } from '@/api/groups'
import { handleApiError } from '@/utils/errorHandler'

const router = useRouter()
const route = useRoute()
const groupStore = useGroupStore()

// 状态
const activeTab = ref('slip')
const selectedGroupId = ref(null)
const groups = ref([])
const processing = ref(false)
const processComplete = ref(false)
const currentMode = ref(null)
const slipSegmentDone = ref(false)   // 新增：单支切割+校验已完成标志

// 进度
const progress = ref({
  total: 0,
  completed: 0,
  failed: 0,
  current_file: null,
  status: 'idle'
})

// 计算属性
const selectedGroup = computed(() => groups.value.find(g => g.id === selectedGroupId.value))
const availableGroups = computed(() => groups.value.filter(g => g.status !== 'exported'))

const getProgressColor = (percentage) => {
  if (percentage < 50) return '#E6A23C'
  if (percentage < 100) return '#409EFF'
  return '#67C23A'
}

// 加载组列表
const loadGroups = async () => {
  try {
    const data = await groupsAPI.getGroups()
    groups.value = data || []
  } catch (error) {
    handleApiError(error, '加载图像组失败')
  }
}

const handleGroupChange = () => {
  processComplete.value = false
  progress.value = { total: 0, completed: 0, failed: 0, current_file: null, status: 'idle' }
}

// 核心：启动切割任务
const handleStartSegment = async (mode) => {
  if (!selectedGroupId.value) return

  // 单字切割前检查单支是否已完成
  if (mode === 'char' && !slipSegmentDone.value) {
    ElMessage.warning('请先完成单支切割和校验')
    return
  }

  processing.value = true
  currentMode.value = mode
  processComplete.value = false

  try {
    let response
    if (mode === 'slip') {
      response = await groupsAPI.segmentSlips(selectedGroupId.value, {})
    } else {
      response = await groupsAPI.segmentChars(selectedGroupId.value, {})
    }

    const batchTaskId = response.batch_task_id
    if (!batchTaskId) {
      throw new Error('未获取到 batch_task_id')
    }

    // 开始轮询
    pollProgress(mode, batchTaskId)
  } catch (error) {
    handleApiError(error, '启动切割失败')
    processing.value = false
  }
}

// 轮询进度（使用 batch_task_id）
const pollProgress = (mode, batchTaskId) => {
  const pollInterval = setInterval(async () => {
    try {
      const response = await groupsAPI.getBatchProgress(selectedGroupId.value, batchTaskId)

      // 更新进度状态
      progress.value = {
        total: response.total || 0,
        completed: response.completed || 0,
        failed: response.failed || 0,
        current_file: null,
        status: response.status
      }

      // Celery 任务完成状态是 SUCCESS 或 FAILURE
      if (response.status === 'SUCCESS') {
        clearInterval(pollInterval)
        processing.value = false
        processComplete.value = true
        ElMessage.success(mode === 'slip' ? '单支切割完成，请进行校验' : '单字切割完成，请进行校验')

        // 跳转到对应校验页
        router.push(`/batch/verify/${selectedGroupId.value}/${mode}`)
      } else if (response.status === 'FAILURE') {
        clearInterval(pollInterval)
        processing.value = false
        ElMessage.error('切割任务失败，请重试')
      }
    } catch (error) {
      clearInterval(pollInterval)
      processing.value = false
      handleApiError(error, '获取进度失败')
    }
  }, 2000)
}

// 从单支切割完成回来（校验完毕后可能从 query 参数得知）
const handleProceedToCharSegment = () => {
  slipSegmentDone.value = true
  activeTab.value = 'char'
  processComplete.value = false
  progress.value = { total: 0, completed: 0, failed: 0, current_file: null, status: 'idle' }
}

const handleProcessComplete = () => {
  router.push('/detail')
}

const resetBatchMode = () => {
  selectedGroupId.value = null
  processComplete.value = false
  slipSegmentDone.value = false
  progress.value = { total: 0, completed: 0, failed: 0, current_file: null, status: 'idle' }
  currentMode.value = null
  loadGroups()
}

const getStatusLabel = (status) => {
  const map = {
    'created': '已创建', 'preprocessing': '预处理中',
    'segmenting': '切割中', 'completed': '已完成', 'exported': '已导出'
  }
  return map[status] || status
}

// 初始化：从 URL query 读取 groupId
onMounted(async () => {
  await loadGroups()

  // 如果从 Groups 页跳转过来，预选组
  const queryGroupId = route.query.groupId
  if (queryGroupId) {
    selectedGroupId.value = queryGroupId
  }

  // 如果从校验页返回且 stage=slip 的校验已完成（通过 query 标志）
  if (route.query.slipVerified === '1') {
    slipSegmentDone.value = true
    activeTab.value = 'char'
    ElMessage.success('单支校验完成，可以开始单字切割')
  }
})
</script>

<style scoped lang="scss">
.batch-seg-page {
  padding: 20px;
  background: #F5F0E8;
  min-height: 100vh;
}

.batch-seg-tabs {
  background: white;
  border-radius: 8px;
  padding: 20px;
}

.batch-mode {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 30px;
  padding: 20px 0;
}

.batch-left {
  h3 {
    margin-bottom: 15px;
    font-size: 16px;
    color: #333;
  }

  .group-info {
    margin-top: 20px;
    padding: 15px;
    background: #f5f5f5;
    border-radius: 4px;
    font-size: 14px;

    p {
      margin: 8px 0;
      color: #666;
    }
  }
}

.batch-right {
  .tips-section {
    background: #f5f7fa;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;

    h4 {
      margin: 0 0 15px 0;
      font-size: 16px;
      color: #333;
    }

    ol {
      margin: 0;
      padding-left: 20px;
      color: #666;
      font-size: 14px;
      line-height: 1.8;
    }
  }

  .start-btn {
    width: 100%;
    margin-top: 20px;
  }
}

.progress-section {
  margin-top: 30px;
  background: white;
  border-radius: 8px;
  padding: 20px;

  h3 {
    margin-bottom: 20px;
    font-size: 16px;
    color: #333;
  }

  .progress-item {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 20px;

    span {
      min-width: 80px;
      font-size: 14px;
      color: #666;
    }

    :deep(.el-progress) {
      flex: 1;
    }
  }

  .current-file {
    padding: 10px;
    background: #f5f5f5;
    border-radius: 4px;
    margin-bottom: 20px;

    p {
      margin: 0;
      font-size: 14px;
      color: #666;
    }
  }
}
</style>
