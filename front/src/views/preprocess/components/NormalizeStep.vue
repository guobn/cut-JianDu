<template>
  <section class="normalize-shell">
    <div class="normalize-grid">
      <section class="panel">
        <h3>归一化参数</h3>
        <el-form label-position="top">
          <el-form-item label="目标长边">
            <el-input-number v-model="form.target_size" :min="256" :max="4096" :step="64" />
          </el-form-item>
          <el-form-item label="保持宽高比">
            <el-switch v-model="form.keep_ratio" />
          </el-form-item>
          <el-form-item label="插值方法">
            <el-radio-group v-model="form.interp">
              <el-radio-button label="nearest">nearest</el-radio-button>
              <el-radio-button label="linear">linear</el-radio-button>
              <el-radio-button label="cubic">cubic</el-radio-button>
              <el-radio-button label="area">area</el-radio-button>
              <el-radio-button label="lanczos4">lanczos4</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="填充颜色">
            <el-radio-group v-model="form.padding">
              <el-radio-button label="white">白色</el-radio-button>
              <el-radio-button label="black">黑色</el-radio-button>
              <el-radio-button label="gray">灰色</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-form>
        <el-button type="primary" size="large" :loading="loading" @click="submit">应用归一化</el-button>
        <el-progress v-if="loading" indeterminate :percentage="100" />
      </section>

      <section class="panel">
        <h3>预览示意</h3>
        <div class="preview-box">
          <LazyProtectedImage
            :src="preview?.file_url || ''"
            :title="preview?.filename || '归一化预览'"
            label="点击查看原图"
            variant="panel"
          />
          <div class="mock-frame" :style="{ width: frameSize, height: frameSize }">
            <span>{{ form.target_size }} x {{ form.target_size }}</span>
          </div>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { usePreprocessStore } from '@/store/preprocess'
import LazyProtectedImage from './LazyProtectedImage.vue'

const props = defineProps({
  groupId: { type: String, required: true }
})

const emit = defineEmits(['done'])

const store = usePreprocessStore()
const loading = ref(false)

const form = reactive({
  target_size: 2048,
  keep_ratio: true,
  interp: 'cubic',
  padding: 'white'
})

const preview = computed(() => store.images[0])
const frameSize = computed(() => `${Math.min(280, Math.max(140, form.target_size / 10))}px`)

const submit = async () => {
  try {
    loading.value = true
    await store.normalize(props.groupId, { ...form })
    ElMessage.success('归一化完成')
    emit('done')
  } catch (error) {
    ElMessage.error(error.message || '归一化失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.normalize-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.panel {
  background: #fff;
  border: 1px solid #eadfcf;
  border-radius: 8px;
  padding: 20px;
}

.panel h3 {
  margin-top: 0;
  color: #3D2817;
}

.preview-box {
  min-height: 360px;
  display: grid;
  place-items: center;
  gap: 18px;
  background: #F5EBD3;
  border-radius: 8px;
  padding: 20px;
}

.mock-frame {
  display: grid;
  place-items: center;
  border: 2px dashed #A93226;
  color: #2C1810;
  background: rgba(255, 255, 255, 0.7);
}

@media (max-width: 900px) {
  .normalize-grid {
    grid-template-columns: 1fr;
  }
}
</style>
