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
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useGroupStore } from '@/store/group'
import { groupsAPI } from '@/api/groups'
import { recognitionAPI } from '@/api/recognition'
import { handleApiError } from '@/utils/errorHandler'

const router = useRouter()
const groupStore = useGroupStore()

// 状态
const activeTab = ref('slip')
const selectedGroupId = ref(null)
const groups = ref([])
const processing = ref(false)
const processComplete = ref(false)
const currentMode = ref(null)

// 进度
const progress = ref({
  total: 0,
  completed: 0,
  current_file: null,
  status: 'idle'
})

// 计算属性
const selectedGroup = computed(() => {
  return groups.value.find(g => g.id === selectedGroupId.value)
})

const availableGroups = computed(() => {
  return groups.value.filter(g => g.status !== 'exported')
})

const getProgressColor = (percentage) => {
  if (percentage < 50) return '#E6A23C'
  if (percentage < 100) return '#409EFF'
  return '#67C23A'
}

// 方法
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
  progress.value = { total: 0, completed: 0, current_file: null, status: 'idle' }
}

const handleStartSegment = async (mode) => {
  if (!selectedGroupId.value) return

  processing.value = true
  currentMode.value = mode
  try {
    if (mode === 'slip') {
      await recognitionAPI.batchDetectSlips(selectedGroupId.value)
    } else {
      await recognitionAPI.batchDetectChars(selectedGroupId.value)
    }

    pollProgress(mode)
  } catch (error) {
    handleApiError(error, '启动切割失败')
    processing.value = false
  }
}

const pollProgress = async (mode) => {
  const pollInterval = setInterval(async () => {
    try {
      const response = await groupsAPI.getProgress(selectedGroupId.value)
      progress.value = response.data

      if (progress.value.status === 'completed') {
        clearInterval(pollInterval)
        processing.value = false
        processComplete.value = true
        ElMessage.success('切割完成')

        // Navigate to verification page based on mode
        if (mode === 'slip') {
          // Navigate to slip verification
          router.push(`/recognition/verify/${selectedGroupId.value}/slip`)
        } else {
          // Navigate to char verification
          router.push(`/recognition/verify/${selectedGroupId.value}/char`)
        }
      }
    } catch (error) {
      clearInterval(pollInterval)
      processing.value = false
      handleApiError(error, '获取进度失败')
    }
  }, 2000)
}

const handleProceedToCharSegment = () => {
  activeTab.value = 'char'
  processComplete.value = false
  progress.value = { total: 0, completed: 0, current_file: null, status: 'idle' }
}

const handleProcessComplete = () => {
  groupStore.setActiveGroup(selectedGroupId.value)
  router.push('/metadata')
}

const resetBatchMode = () => {
  selectedGroupId.value = null
  processComplete.value = false
  progress.value = { total: 0, completed: 0, current_file: null, status: 'idle' }
  currentMode.value = null
  loadGroups()
}

const getStatusLabel = (status) => {
  const map = {
    'created': '已创建',
    'preprocessing': '预处理中',
    'segmenting': '切割中',
    'completed': '已完成',
    'exported': '已导出'
  }
  return map[status] || status
}

// 初始化
onMounted(() => {
  loadGroups()
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
