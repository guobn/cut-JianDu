<template>
  <div class="preprocess-page">
    <!-- 模式切换 Tab -->
    <el-tabs v-model="activeTab" class="preprocess-tabs">
      <!-- Tab 1: 单图处理 -->
      <el-tab-pane label="单图处理" name="single">
        <div class="single-mode">
          <el-empty description="单图处理功能开发中" />
        </div>
      </el-tab-pane>

      <!-- Tab 2: 图像组批量处理 -->
      <el-tab-pane label="图像组批量处理" name="batch">
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

          <!-- 右侧：批处理配置面板 -->
          <div class="batch-right">
            <el-collapse>
              <!-- 尺寸归一化 -->
              <el-collapse-item title="尺寸归一化" name="1">
                <div class="config-item">
                  <label>目标长边像素</label>
                  <el-slider
                    v-model="preprocessConfig.target_long_side"
                    :min="500"
                    :max="4000"
                    :step="100"
                    show-input
                  />
                </div>
                <div class="config-item">
                  <el-checkbox v-model="preprocessConfig.keep_aspect_ratio">
                    保持宽高比
                  </el-checkbox>
                </div>
              </el-collapse-item>

              <!-- 旋转校正 -->
              <el-collapse-item title="旋转校正" name="2">
                <div class="config-item">
                  <el-checkbox v-model="preprocessConfig.auto_rotate">
                    启用自动旋转检测
                  </el-checkbox>
                </div>
                <div v-if="!preprocessConfig.auto_rotate" class="config-item">
                  <label>固定旋转角度</label>
                  <el-input-number
                    v-model="preprocessConfig.fixed_rotation_angle"
                    :min="-180"
                    :max="180"
                    :step="1"
                  />
                </div>
              </el-collapse-item>

              <!-- 色彩处理 -->
              <el-collapse-item title="色彩处理" name="3">
                <div class="config-item">
                  <el-checkbox v-model="preprocessConfig.grayscale">
                    灰度化
                  </el-checkbox>
                </div>
                <div class="config-item">
                  <el-checkbox v-model="preprocessConfig.clahe_enabled">
                    对比度增强 CLAHE
                  </el-checkbox>
                </div>
                <div class="config-item">
                  <label>去噪强度</label>
                  <el-slider
                    v-model="preprocessConfig.denoise_strength"
                    :min="0"
                    :max="5"
                    :step="1"
                    show-input
                  />
                </div>
              </el-collapse-item>

              <!-- 输出设置 -->
              <el-collapse-item title="输出设置" name="4">
                <div class="config-item">
                  <label>输出格式</label>
                  <el-select v-model="preprocessConfig.output_format">
                    <el-option label="PNG" value="PNG" />
                    <el-option label="JPEG" value="JPEG" />
                  </el-select>
                </div>
                <div class="config-item">
                  <el-checkbox v-model="preprocessConfig.overwrite_original">
                    覆盖原图
                  </el-checkbox>
                </div>
              </el-collapse-item>
            </el-collapse>

            <!-- 开始处理按钮 -->
            <el-button
              type="primary"
              class="start-btn"
              :disabled="!selectedGroupId || processing"
              :loading="processing"
              @click="handleStartPreprocess"
            >
              开始批量处理
            </el-button>
          </div>
        </div>

        <!-- 进度显示区域 -->
        <div v-if="processing" class="progress-section">
          <h3>处理进度</h3>

          <!-- 总进度条 -->
          <div class="progress-item">
            <span>总进度</span>
            <el-progress
              :percentage="Math.round((progress.completed / progress.total) * 100)"
              :color="getProgressColor"
            />
            <span>{{ progress.completed }}/{{ progress.total }} 张</span>
          </div>

          <!-- 当前处理文件 -->
          <div v-if="progress.current_file" class="current-file">
            <p>处理中：{{ progress.current_file }}</p>
          </div>

          <!-- 预览区域 -->
          <div class="preview-area">
            <div class="preview-left">
              <p>原始图像</p>
              <img v-if="currentImageUrl" :src="currentImageUrl" alt="原始图像" />
            </div>
            <div class="preview-right">
              <p>处理结果预览</p>
              <canvas ref="previewCanvas" class="preview-canvas" />
            </div>
          </div>
        </div>

        <!-- 完成提示 -->
        <el-result
          v-if="processComplete"
          icon="success"
          title="处理完成"
          :sub-title="`已处理 ${progress.completed} 张图像`"
        >
          <template #extra>
            <el-button type="primary" @click="handleProcessComplete">
              前往切割页面
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
import { handleApiError } from '@/utils/errorHandler'

const router = useRouter()
const groupStore = useGroupStore()

// 状态
const activeTab = ref('batch')
const selectedGroupId = ref(null)
const groups = ref([])
const processing = ref(false)
const processComplete = ref(false)
const currentImageUrl = ref(null)
const previewCanvas = ref(null)

// 进度
const progress = ref({
  total: 0,
  completed: 0,
  current_file: null,
  status: 'idle'
})

// 预处理配置
const preprocessConfig = ref({
  target_long_side: 2000,
  keep_aspect_ratio: true,
  auto_rotate: true,
  fixed_rotation_angle: 0,
  grayscale: false,
  clahe_enabled: true,
  denoise_strength: 2,
  output_format: 'PNG',
  overwrite_original: false
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
    const response = await groupsAPI.getGroups()
    groups.value = response.data
  } catch (error) {
    handleApiError(error, '加载图像组失败')
  }
}

const handleGroupChange = () => {
  processComplete.value = false
  progress.value = { total: 0, completed: 0, current_file: null, status: 'idle' }
}

const handleStartPreprocess = async () => {
  if (!selectedGroupId.value) return

  processing.value = true
  try {
    // 调用后端批量预处理 API
    const response = await groupsAPI.preprocessGroup(selectedGroupId.value, preprocessConfig.value)

    // 开始轮询进度
    pollProgress()
  } catch (error) {
    handleApiError(error, '启动预处理失败')
    processing.value = false
  }
}

const pollProgress = async () => {
  const pollInterval = setInterval(async () => {
    try {
      const response = await groupsAPI.getProgress(selectedGroupId.value)
      progress.value = response.data

      if (progress.value.status === 'completed') {
        clearInterval(pollInterval)
        processing.value = false
        processComplete.value = true
        ElMessage.success('预处理完成')
      }
    } catch (error) {
      clearInterval(pollInterval)
      processing.value = false
      handleApiError(error, '获取进度失败')
    }
  }, 2000)
}

const handleProcessComplete = () => {
  // 更新 store 中的活跃组
  groupStore.setActiveGroup(selectedGroupId.value)
  // 跳转到批量切割页面
  router.push('/batch-segmentation')
}

const resetBatchMode = () => {
  selectedGroupId.value = null
  processComplete.value = false
  progress.value = { total: 0, completed: 0, current_file: null, status: 'idle' }
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
.preprocess-page {
  padding: 20px;
  background: #F5F0E8;
  min-height: 100vh;
}

.preprocess-tabs {
  background: white;
  border-radius: 8px;
  padding: 20px;
}

.single-mode {
  padding: 40px;
  text-align: center;
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
  .config-item {
    margin-bottom: 15px;

    label {
      display: block;
      margin-bottom: 8px;
      font-size: 14px;
      color: #333;
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

  .preview-area {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-top: 20px;

    p {
      margin-bottom: 10px;
      font-size: 14px;
      color: #666;
    }

    img,
    .preview-canvas {
      width: 100%;
      height: 300px;
      background: #f5f5f5;
      border-radius: 4px;
      object-fit: contain;
    }
  }
}
</style>
