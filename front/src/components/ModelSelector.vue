<template>
  <div class="model-selector">
    <div class="model-selector__header">
      <el-icon class="model-selector__icon"><Cpu /></el-icon>
      <span class="model-selector__title">检测引擎</span>
    </div>

    <el-select
      v-model="selectedEngine"
      placeholder="选择检测引擎"
      size="default"
      class="model-selector__select"
      :popper-class="'model-selector-popper'"
      @change="handleEngineChange"
    >
      <el-option
        v-for="engine in availableEngines"
        :key="engine.value"
        :label="engine.label"
        :value="engine.value"
      >
        <div class="model-selector__option">
          <span class="model-selector__option-label">{{ engine.label }}</span>
          <span class="model-selector__option-desc">{{ getEngineDescription(engine.value) }}</span>
        </div>
      </el-option>
    </el-select>

    <div v-if="showParams" class="model-selector__params">
      <div class="model-selector__params-title">
        <el-icon><Setting /></el-icon>
        <span>SAHI 参数配置</span>
      </div>

      <el-descriptions :column="1" size="small" border>
        <el-descriptions-item label="切片尺寸">
          {{ currentParams.slice_size }}px
        </el-descriptions-item>
        <el-descriptions-item label="重叠率">
          {{ (currentParams.overlap_ratio * 100).toFixed(0) }}%
        </el-descriptions-item>
        <el-descriptions-item label="Soft-NMS">
          <el-tag :type="currentParams.use_soft_nms ? 'success' : 'info'" size="small">
            {{ currentParams.use_soft_nms ? '启用' : '禁用' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <div v-if="description" class="model-selector__description">
      <el-alert :title="description" type="info" :closable="false" show-icon />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Cpu, Setting } from '@element-plus/icons-vue'
import { useImageProcessingStore } from '@/store/imageProcessing'
import {
  DETECT_ENGINE_DESCRIPTIONS,
  DETECT_ENGINE_SHORT_DESCRIPTIONS,
  SLIP_DETECT_ENGINES,
  CHARACTER_DETECT_ENGINES
} from '@/config/engineParams'

const props = defineProps({
  modelValue: {
    type: String,
    default: 'yolov8'
  },
  showParams: {
    type: Boolean,
    default: true
  },
  showDescription: {
    type: Boolean,
    default: true
  },
  // 检测模式：'slip' 单支检测 或 'character' 单字检测
  // 用于区分显示不同的模型选项
  mode: {
    type: String,
    default: 'slip',
    validator: (value) => ['slip', 'character'].includes(value)
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const imageStore = useImageProcessingStore()

const selectedEngine = ref(props.modelValue)

// 根据 mode 过滤可用的引擎列表
const availableEngines = computed(() => {
  if (props.mode === 'slip') {
    return SLIP_DETECT_ENGINES
  } else {
    return CHARACTER_DETECT_ENGINES
  }
})

const currentParams = computed(() => {
  return imageStore.getEngineParams(selectedEngine.value)
})

const description = computed(() => {
  return props.showDescription ? DETECT_ENGINE_DESCRIPTIONS[selectedEngine.value] : null
})

watch(() => props.modelValue, (newVal) => {
  if (newVal !== selectedEngine.value) {
    selectedEngine.value = newVal
  }
})

/**
 * 获取引擎描述
 */
function getEngineDescription(engineType) {
  return DETECT_ENGINE_SHORT_DESCRIPTIONS[engineType] || ''
}

/**
 * 引擎变化处理
 */
function handleEngineChange(engine) {
  imageStore.setActiveEngine(engine, props.mode)
  emit('update:modelValue', engine)
  emit('change', {
    engine,
    params: imageStore.getEngineParams(engine)
  })
}
</script>

<style scoped>
.model-selector {
  width: 100%;
  padding: 16px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.model-selector__header {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.model-selector__icon {
  font-size: 18px;
  color: #409EFF;
  margin-right: 8px;
}

.model-selector__title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2d3d;
}

.model-selector__select {
  width: 100%;
}

.model-selector__option {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.model-selector__option-label {
  font-weight: 600;
  color: #1f2d3d;
}

.model-selector__option-desc {
  font-size: 12px;
  color: rgba(31, 45, 61, 0.6);
}

.model-selector__params {
  margin-top: 16px;
  padding: 12px;
  background: rgba(64, 158, 255, 0.04);
  border-radius: 8px;
  border: 1px solid rgba(64, 158, 255, 0.15);
}

.model-selector__params-title {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 600;
  color: #409EFF;
}

.model-selector__params-title .el-icon {
  margin-right: 6px;
}

.model-selector__description {
  margin-top: 12px;
}

.model-selector__description :deep(.el-alert) {
  padding: 10px 12px;
}

.model-selector__description :deep(.el-alert--info) {
  background: rgba(144, 147, 153, 0.04);
  border-color: rgba(144, 147, 153, 0.15);
}

.model-selector__description :deep(.el-alert__title) {
  font-size: 12px;
}

/* 下拉框样式 */
:deep(.model-selector-popper) {
  .el-select-dropdown__item {
    padding: 8px 12px;
  }

  .el-select-dropdown__item.selected {
    background-color: rgba(64, 158, 255, 0.08);
  }
}
</style>
