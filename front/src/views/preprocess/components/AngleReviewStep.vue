<template>
  <section class="review-shell">
    <el-alert
      v-if="allAutoPass"
      type="success"
      :closable="false"
      show-icon
      title="所有图已自动通过，可直接应用旋转"
    />
    <el-alert
      v-else-if="allLowConfidence"
      type="warning"
      :closable="false"
      show-icon
      title="自动检测置信度普遍偏低，建议检查原图清晰度"
    />

    <div class="summary-card">
      <div>
        <h3>角度审核</h3>
        <p>{{ confirmedCount }} / {{ totalCount }} 已确认，{{ pendingCount }} 待处理</p>
      </div>
      <el-progress :percentage="completionPercent" :color="progressColor" />
    </div>

    <el-table :data="rows" :row-class-name="rowClassName" empty-text="还没有角度结果">
      <el-table-column label="缩略图" width="92">
        <template #default="{ row }">
          <LazyProtectedImage
            :src="row.file_url"
            :title="row.filename"
            label="查看"
          />
        </template>
      </el-table-column>

      <el-table-column prop="filename" label="文件名" min-width="200" />

      <el-table-column label="估测角度" width="220">
        <template #default="{ row }">
          <div v-if="editingId === row.image_id" class="edit-angle">
            <el-input-number v-model="editingAngle" :step="0.1" :precision="2" />
            <el-button link type="primary" :loading="busyId === row.image_id" @click="saveEdit(row)">确认</el-button>
            <el-button link @click="cancelEdit">取消</el-button>
          </div>
          <span v-else>{{ formatAngle(row.rotation_angle) }}</span>
        </template>
      </el-table-column>

      <el-table-column label="置信度" width="110">
        <template #default="{ row }">
          <el-progress
            type="circle"
            :width="48"
            :stroke-width="6"
            :percentage="Math.round((row.rotation_confidence || 0) * 100)"
            :color="confidenceColor(row.rotation_confidence)"
          />
        </template>
      </el-table-column>

      <el-table-column label="状态" width="150">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row)">{{ statusLabel(row) }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column label="操作" min-width="240">
        <template #default="{ row }">
          <div class="row-actions">
            <el-button
              v-if="(row.rotation_confidence || 0) >= 0.3 && row.review_state !== 'accepted' && !row.preprocess_skipped"
              size="small"
              type="success"
              :loading="busyId === row.image_id"
              @click="acceptRow(row)"
            >
              接受
            </el-button>
            <el-button
              size="small"
              :disabled="row.preprocess_skipped"
              :loading="busyId === row.image_id"
              @click="startEdit(row)"
            >
              修改
            </el-button>
            <el-popconfirm title="跳过这张图的预处理？" @confirm="skipRow(row)">
              <template #reference>
                <el-button size="small" text type="danger" :loading="busyId === row.image_id">跳过不处理</el-button>
              </template>
            </el-popconfirm>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <div class="footer-actions">
      <el-button :disabled="autoPassRows.length === 0" @click="acceptAllAutoPass">全部接受默认</el-button>
      <el-button type="primary" size="large" :disabled="!canApplyRotation" @click="$emit('apply-rotation')">
        应用旋转 →
      </el-button>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePreprocessStore } from '@/store/preprocess'
import LazyProtectedImage from './LazyProtectedImage.vue'

const props = defineProps({
  groupId: { type: String, required: true }
})

defineEmits(['apply-rotation'])

const store = usePreprocessStore()

const editingId = ref('')
const editingAngle = ref(0)
const busyId = ref('')

const rows = computed(() => store.images)
const totalCount = computed(() => rows.value.length)
const autoPassRows = computed(() => rows.value.filter((row) => row.status === 'auto_pass' && !row.preprocess_skipped))
const confirmedCount = computed(() => rows.value.filter((row) => (
  row.preprocess_skipped || row.review_state === 'accepted' || row.status === 'auto_pass'
)).length)
const pendingCount = computed(() => Math.max(0, totalCount.value - confirmedCount.value))
const completionPercent = computed(() => totalCount.value ? Math.round((confirmedCount.value / totalCount.value) * 100) : 0)
const allAutoPass = computed(() => totalCount.value > 0 && rows.value.every((row) => row.status === 'auto_pass'))
const allLowConfidence = computed(() => totalCount.value > 0 && rows.value.every((row) => row.status === 'low_confidence'))
const canApplyRotation = computed(() => rows.value.every((row) => (
  row.preprocess_skipped || row.review_state === 'accepted' || row.status === 'auto_pass'
)))

const progressColor = [
  { color: '#A93226', percentage: 30 },
  { color: '#c9872b', percentage: 70 },
  { color: '#3D2817', percentage: 100 }
]

const confidenceColor = (value) => {
  if ((value || 0) >= 0.7) return '#3D2817'
  if ((value || 0) >= 0.3) return '#c9872b'
  return '#A93226'
}

const statusLabel = (row) => {
  if (row.preprocess_skipped) return '已跳过'
  if (row.review_state === 'accepted') return '已接受'
  if (row.status === 'auto_pass') return '自动通过'
  if (row.status === 'review_required') return '待复核'
  return '低置信度'
}

const statusTagType = (row) => {
  if (row.preprocess_skipped) return 'info'
  if (row.review_state === 'accepted') return 'success'
  if (row.status === 'auto_pass') return 'success'
  if (row.status === 'review_required') return 'warning'
  return 'danger'
}

const formatAngle = (value) => `${Number(value || 0).toFixed(2)}°`

const rowClassName = ({ row }) => (row.preprocess_skipped ? 'row-skipped' : '')

const reload = async () => {
  try {
    await store.fetchAngles(props.groupId)
  } catch (error) {
    ElMessage.error(error.message || '加载角度失败')
  }
}

onMounted(reload)

const startEdit = (row) => {
  editingId.value = row.image_id
  editingAngle.value = Number(row.rotation_angle || 0)
}

const cancelEdit = () => {
  editingId.value = ''
}

const saveEdit = async (row) => {
  try {
    busyId.value = row.image_id
    await store.patchAngle(props.groupId, row.image_id, {
      rotation_angle: editingAngle.value,
      accepted: true,
      preprocess_skipped: false
    })
    editingId.value = ''
    ElMessage.success('角度已更新')
  } catch (error) {
    ElMessage.error(error.message || '更新失败')
  } finally {
    busyId.value = ''
  }
}

const acceptRow = async (row) => {
  try {
    busyId.value = row.image_id
    await store.patchAngle(props.groupId, row.image_id, {
      accepted: true,
      preprocess_skipped: false
    })
  } catch (error) {
    ElMessage.error(error.message || '接受失败')
  } finally {
    busyId.value = ''
  }
}

const skipRow = async (row) => {
  try {
    busyId.value = row.image_id
    await store.patchAngle(props.groupId, row.image_id, {
      preprocess_skipped: true,
      accepted: false
    })
    ElMessage.success('已跳过')
  } catch (error) {
    ElMessage.error(error.message || '跳过失败')
  } finally {
    busyId.value = ''
  }
}

const acceptAllAutoPass = async () => {
  try {
    await ElMessageBox.confirm('只会批量接受自动通过的图片。', '确认接受')
    for (const row of autoPassRows.value) {
      await store.patchAngle(props.groupId, row.image_id, {
        accepted: true,
        preprocess_skipped: false
      })
    }
    ElMessage.success('自动通过项已确认')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '批量接受失败')
    }
  }
}
</script>

<style scoped>
.review-shell {
  display: grid;
  gap: 18px;
}

.summary-card {
  display: grid;
  grid-template-columns: 1fr 240px;
  gap: 20px;
  align-items: center;
  padding: 20px;
  background: #fff;
  border: 1px solid #eadfcf;
  border-radius: 8px;
}

.summary-card h3 {
  margin: 0 0 6px;
  color: #3D2817;
}

.summary-card p {
  margin: 0;
  color: #2C1810;
}

.edit-angle,
.row-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

:deep(.row-skipped) {
  background: rgba(245, 235, 211, 0.55);
  color: #7f6755;
}

@media (max-width: 900px) {
  .summary-card {
    grid-template-columns: 1fr;
  }
}
</style>
