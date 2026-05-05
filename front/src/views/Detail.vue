<template>
  <div class="detail-page">
    <div class="detail-header">
      <h2>简牍图像展示和管理</h2>
      <p>多层级展示：图像组 -> 单支 -> 单字，同时保留原图查看入口</p>
    </div>

    <div class="detail-container">
      <div class="tree-panel">
        <div class="tree-header">
          <h3>图像组织结构</h3>
          <el-button type="primary" size="small" @click="loadGroups">刷新</el-button>
        </div>

        <el-tree
          ref="treeRef"
          :data="treeData"
          :props="treeProps"
          node-key="id"
          class="tree-content"
          :expand-on-click-node="false"
          @node-click="handleNodeClick"
        >
          <template #default="{ node, data }">
            <div class="tree-node">
              <el-icon v-if="data.type === 'group'" class="node-icon"><FolderOpened /></el-icon>
              <el-icon v-else-if="data.type === 'slip-folder' || data.type === 'slip-chars-placeholder'" class="node-icon"><Folder /></el-icon>
              <el-icon v-else-if="data.type === 'image'" class="node-icon"><Picture /></el-icon>
              <el-icon v-else-if="data.type === 'slip'" class="node-icon"><DocumentCopy /></el-icon>
              <el-icon v-else class="node-icon"><Document /></el-icon>
              <span class="node-label">{{ node.label }}</span>
              <span v-if="data.count !== undefined && data.count !== null" class="node-count">({{ data.count }})</span>
            </div>
          </template>
        </el-tree>
      </div>

      <div class="content-panel">
        <div v-if="selectedNode && selectedNode.type === 'group'" class="content-section">
          <div class="section-header">
            <h3>{{ selectedNode.name }}</h3>
            <el-tag>图像组</el-tag>
          </div>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="组名">{{ selectedNode.name }}</el-descriptions-item>
            <el-descriptions-item label="来源">{{ selectedNode.source_site || '-' }}</el-descriptions-item>
            <el-descriptions-item label="时期">{{ selectedNode.period || '-' }}</el-descriptions-item>
            <el-descriptions-item label="材质">{{ selectedNode.material || '-' }}</el-descriptions-item>
            <el-descriptions-item label="收藏">{{ selectedNode.collection || '-' }}</el-descriptions-item>
            <el-descriptions-item label="出土年份">{{ selectedNode.excavation_year || '-' }}</el-descriptions-item>
            <el-descriptions-item label="批号">{{ selectedNode.batch_no || '-' }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag>{{ getStatusLabel(selectedNode.status) }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-value">{{ selectedNode.total_images || 0 }}</div>
              <div class="stat-label">原始图像</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{{ selectedNode.processed_images || 0 }}</div>
              <div class="stat-label">已处理</div>
            </div>
          </div>

          <div class="action-buttons">
            <el-button type="primary" @click="handleExportGroup">导出数据</el-button>
            <el-button @click="handleEditGroup">编辑信息</el-button>
          </div>
        </div>

        <div v-else-if="selectedNode && selectedNode.type === 'image'" class="content-section">
          <div class="section-header">
            <h3>{{ selectedNode.filename }}</h3>
            <el-tag>原图</el-tag>
          </div>
          <div class="image-preview">
            <img v-if="previewUrl" :src="previewUrl" :alt="selectedNode.filename" />
            <p v-else class="no-image">暂无图像预览</p>
          </div>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="文件名">{{ selectedNode.filename }}</el-descriptions-item>
            <el-descriptions-item label="尺寸">{{ selectedNode.width }} x {{ selectedNode.height }}</el-descriptions-item>
            <el-descriptions-item label="格式">{{ selectedNode.format || '-' }}</el-descriptions-item>
            <el-descriptions-item label="大小">{{ formatFileSize(selectedNode.file_size) }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <div v-else-if="selectedNode && (selectedNode.type === 'slip-folder' || selectedNode.type === 'slip')" class="content-section">
          <div class="section-header">
            <h3>{{ selectedNode.name }}</h3>
            <el-tag type="success">单支</el-tag>
          </div>

          <div class="image-preview">
            <img v-if="previewUrl" :src="previewUrl" :alt="selectedNode.name" />
            <p v-else class="no-image">暂无单支预览</p>
          </div>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="ID">{{ selectedNode.segment_id || selectedNode.slip_id }}</el-descriptions-item>
            <el-descriptions-item label="置信度">{{ formatConfidence(selectedNode.confidence) }}</el-descriptions-item>
            <el-descriptions-item label="尺寸">{{ selectedNode.width }} x {{ selectedNode.height }}</el-descriptions-item>
            <el-descriptions-item label="校验状态">{{ selectedNode.validated ? '已校验' : '未校验' }}</el-descriptions-item>
          </el-descriptions>

          <h4>元数据标注</h4>
          <el-form :model="slipMetadataForm" label-width="110px" class="metadata-form">
            <el-form-item label="单支编号">
              <el-input v-model="slipMetadataForm.slip_id" placeholder="输入单支编号" />
            </el-form-item>
            <el-form-item label="文字内容">
              <el-input v-model="slipMetadataForm.content_text" type="textarea" :rows="3" placeholder="输入文字内容" />
            </el-form-item>
            <el-form-item label="保存状况">
              <el-select v-model="slipMetadataForm.condition" placeholder="选择保存状况">
                <el-option label="完好" value="完好" />
                <el-option label="轻微破损" value="轻微破损" />
                <el-option label="中度破损" value="中度破损" />
                <el-option label="严重破损" value="严重破损" />
              </el-select>
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model="slipMetadataForm.notes" type="textarea" :rows="2" placeholder="输入备注信息" />
            </el-form-item>
          </el-form>

          <div class="action-buttons">
            <el-button type="primary" @click="handleSaveSlipMetadata">保存元数据</el-button>
          </div>
        </div>

        <div v-else-if="selectedNode && selectedNode.type === 'char'" class="content-section">
          <div class="section-header">
            <h3>{{ selectedNode.name }}</h3>
            <el-tag type="warning">单字</el-tag>
          </div>

          <div class="image-preview">
            <img v-if="previewUrl" :src="previewUrl" :alt="selectedNode.name" />
            <p v-else class="no-image">暂无单字预览</p>
          </div>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="ID">{{ selectedNode.segment_id }}</el-descriptions-item>
            <el-descriptions-item label="置信度">{{ formatConfidence(selectedNode.confidence) }}</el-descriptions-item>
            <el-descriptions-item label="尺寸">{{ selectedNode.width }} x {{ selectedNode.height }}</el-descriptions-item>
            <el-descriptions-item label="校验状态">{{ selectedNode.validated ? '已校验' : '未校验' }}</el-descriptions-item>
          </el-descriptions>

          <h4>元数据标注</h4>
          <el-form :model="charMetadataForm" label-width="110px" class="metadata-form">
            <el-form-item label="字符标注">
              <el-input v-model="charMetadataForm.char_label" placeholder="输入字符标注" />
            </el-form-item>
            <el-form-item label="Unicode">
              <el-input v-model="charMetadataForm.char_unicode" placeholder="输入 Unicode 编码" />
            </el-form-item>
            <el-form-item label="人工置信度">
              <el-input-number v-model="charMetadataForm.confidence_override" :min="0" :max="1" :step="0.1" />
            </el-form-item>
          </el-form>

          <div class="action-buttons">
            <el-button type="primary" @click="handleSaveCharMetadata">保存元数据</el-button>
          </div>
        </div>

        <div v-else class="empty-state">
          <el-empty description="请从左侧选择要查看的内容" />
        </div>
      </div>
    </div>

    <el-dialog v-model="showEditDialog" title="编辑图像组信息" width="500px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="组名称"><el-input v-model="editForm.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="editForm.description" type="textarea" /></el-form-item>
        <el-form-item label="出土地点"><el-input v-model="editForm.source_site" /></el-form-item>
        <el-form-item label="时代断代"><el-input v-model="editForm.period" /></el-form-item>
        <el-form-item label="材质"><el-input v-model="editForm.material" /></el-form-item>
        <el-form-item label="收藏机构"><el-input v-model="editForm.collection" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSaveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, DocumentCopy, Folder, FolderOpened, Picture } from '@element-plus/icons-vue'

import pinia from '@/store'
import { useUserStore } from '@/store/user'
import { groupsAPI } from '@/api/groups'
import { metadataAPI } from '@/api/metadata'
import { handleApiError } from '@/utils/errorHandler'

const API_BASE_URL = import.meta.env.VITE_BACKEND_BASE_URL || 'http://127.0.0.1:8000'

const route = useRoute()
const userStore = useUserStore(pinia)
const treeRef = ref(null)
const groups = ref([])
const treeData = ref([])
const selectedNode = ref(null)
const previewUrl = ref('')
const previewObjectUrl = ref('')

const showEditDialog = ref(false)
const editForm = ref({
  name: '',
  description: '',
  source_site: '',
  period: '',
  material: '',
  collection: ''
})

const slipMetadataForm = ref({
  slip_id: '',
  content_text: '',
  condition: '',
  notes: ''
})

const charMetadataForm = ref({
  char_label: '',
  char_unicode: '',
  confidence_override: 1.0
})

const treeProps = {
  children: 'children',
  label: (data) => data.name || data.filename || data.id
}

const revokePreview = () => {
  if (previewObjectUrl.value) {
    URL.revokeObjectURL(previewObjectUrl.value)
    previewObjectUrl.value = ''
  }
  previewUrl.value = ''
}

const buildGroupNode = (group) => ({
  id: `group-${group.id}`,
  type: 'group',
  name: group.name,
  source_site: group.source_site,
  period: group.period,
  material: group.material,
  collection: group.collection,
  excavation_year: group.excavation_year,
  batch_no: group.batch_no,
  status: group.status,
  total_images: group.total_images,
  processed_images: group.processed_images,
  childrenLoaded: false,
  children: []
})

const loadGroups = async () => {
  try {
    const data = await groupsAPI.getGroups()
    groups.value = data || []
    treeData.value = groups.value.map(buildGroupNode)
  } catch (error) {
    handleApiError(error, '加载图像组失败')
  }
}

const ensureGroupChildrenLoaded = async (groupNode) => {
  if (!groupNode || groupNode.childrenLoaded) return

  const groupId = groupNode.id.replace('group-', '')
  const [imagesResp, slips] = await Promise.all([
    groupsAPI.getGroupImages(groupId),
    groupsAPI.getGroupSegments(groupId, { type: 'slip' })
  ])

  const images = imagesResp.items || []
  const slipFolders = (slips || []).map((slip, idx) => ({
    id: `slip-folder-${slip.id}`,
    type: 'slip-folder',
    name: `单支${idx + 1}`,
    segment_id: slip.id,
    slip_id: slip.id,
    source_image_id: slip.source_image_id,
    group_id: groupId,
    width: slip.bbox_width,
    height: slip.bbox_height,
    confidence: slip.confidence,
    validated: slip.validated,
    children: [
      {
        id: `chars-${slip.id}`,
        type: 'slip-chars-placeholder',
        name: '单字（点击加载）',
        slip_id: slip.id,
        group_id: groupId,
        children: []
      }
    ]
  }))

  const imageNodes = images.map((img, idx) => ({
    id: `image-${img.id}`,
    type: 'image',
    name: `原图${idx + 1}`,
    filename: img.filename,
    source_image_id: img.id,
    group_id: groupId,
    width: img.width,
    height: img.height,
    format: img.format,
    file_size: img.file_size
  }))

  groupNode.children = [...slipFolders, ...imageNodes]
  groupNode.childrenLoaded = true
  treeRef.value?.updateKeyChildren(groupNode.id, groupNode.children)
}

const handleNodeClick = async (data) => {
  if (data.type === 'group') {
    try {
      await ensureGroupChildrenLoaded(data)
    } catch (error) {
      handleApiError(error, '加载图像组结构失败')
    }
    selectedNode.value = data
    return
  }

  if (data.type === 'slip-chars-placeholder') {
    if (data.children.length === 0) {
      try {
        const chars = await groupsAPI.getGroupSegments(data.group_id, {
          type: 'char',
          parentSegmentId: data.slip_id
        })
        data.children = (chars || []).map((char, idx) => ({
          id: `char-${char.id}`,
          type: 'char',
          name: `单字${idx + 1}`,
          segment_id: char.id,
          source_image_id: char.source_image_id,
          parent_segment_id: char.parent_segment_id,
          group_id: data.group_id,
          width: char.bbox_width,
          height: char.bbox_height,
          confidence: char.confidence,
          validated: char.validated
        }))
        treeRef.value?.updateKeyChildren(data.id, data.children)
      } catch (error) {
        handleApiError(error, '加载单字失败')
      }
    }
    return
  }

  if (['image', 'slip-folder', 'slip', 'char'].includes(data.type)) {
    selectedNode.value = data
  }
}

const loadProtectedPreview = async (node) => {
  revokePreview()
  if (!node) return

  const token = userStore.session?.access_token || ''
  let targetUrl = ''

  if (node.type === 'image') {
    targetUrl = `${API_BASE_URL}/api/groups/${node.group_id}/images/${node.source_image_id}/file`
  } else if (node.type === 'slip-folder' || node.type === 'slip' || node.type === 'char') {
    const segmentId = node.segment_id || node.slip_id
    targetUrl = `${API_BASE_URL}/api/groups/${node.group_id}/segments/${segmentId}/file`
  }

  if (!targetUrl) return

  try {
    const resp = await fetch(targetUrl, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const blob = await resp.blob()
    previewObjectUrl.value = URL.createObjectURL(blob)
    previewUrl.value = previewObjectUrl.value
  } catch (error) {
    console.warn('加载预览失败', error)
    previewUrl.value = ''
  }
}

const handleExportGroup = async () => {
  if (!selectedNode.value || selectedNode.value.type !== 'group') return
  const groupId = selectedNode.value.id.replace('group-', '')
  let format = 'msj'

  try {
    await ElMessageBox.confirm('点击“MSJ 格式”导出，点击“COCO 格式”则导出 COCO。', '导出数据', {
      distinguishCancelAndClose: true,
      confirmButtonText: 'MSJ 格式',
      cancelButtonText: 'COCO 格式'
    })
  } catch (e) {
    if (e === 'cancel') {
      format = 'coco'
    } else {
      return
    }
  }

  try {
    const response = await groupsAPI.exportGroup(groupId, { format, include_images: true })
    ElMessage.success(`导出成功，格式：${format}`)
    if (response.file_url) {
      window.open(`${API_BASE_URL}${response.file_url}`, '_blank')
    }
  } catch (error) {
    handleApiError(error, '导出失败')
  }
}

const handleEditGroup = () => {
  if (!selectedNode.value || selectedNode.value.type !== 'group') return
  Object.assign(editForm.value, {
    name: selectedNode.value.name,
    description: selectedNode.value.description,
    source_site: selectedNode.value.source_site,
    period: selectedNode.value.period,
    material: selectedNode.value.material,
    collection: selectedNode.value.collection
  })
  showEditDialog.value = true
}

const handleSaveEdit = async () => {
  if (!selectedNode.value || selectedNode.value.type !== 'group') return
  const groupId = selectedNode.value.id.replace('group-', '')
  try {
    await groupsAPI.updateGroup(groupId, editForm.value)
    Object.assign(selectedNode.value, editForm.value)
    showEditDialog.value = false
    ElMessage.success('已保存')
    await loadGroups()
  } catch (error) {
    handleApiError(error, '保存失败')
  }
}

const handleSaveSlipMetadata = async () => {
  if (!selectedNode.value || !['slip-folder', 'slip'].includes(selectedNode.value.type)) return
  try {
    await metadataAPI.saveSegmentMetadata(selectedNode.value.segment_id || selectedNode.value.slip_id, {
      title: slipMetadataForm.value.slip_id,
      content_description: slipMetadataForm.value.content_text,
      event_type: slipMetadataForm.value.condition,
      extra: { notes: slipMetadataForm.value.notes }
    })
    ElMessage.success('单支元数据已保存')
  } catch (error) {
    handleApiError(error, '保存元数据失败')
  }
}

const handleSaveCharMetadata = async () => {
  if (!selectedNode.value || selectedNode.value.type !== 'char') return
  try {
    await metadataAPI.saveSegmentMetadata(selectedNode.value.segment_id, {
      title: charMetadataForm.value.char_label,
      content_description: charMetadataForm.value.char_unicode,
      extra: { confidence_override: charMetadataForm.value.confidence_override }
    })
    ElMessage.success('单字元数据已保存')
  } catch (error) {
    handleApiError(error, '保存元数据失败')
  }
}

const getStatusLabel = (status) => {
  const map = {
    created: '已创建',
    preprocessing: '预处理中',
    segmenting: '切割中',
    completed: '已完成',
    exported: '已导出'
  }
  return map[status] || status
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${Math.round((bytes / Math.pow(k, i)) * 100) / 100} ${sizes[i]}`
}

const formatConfidence = (value) => (value || value === 0 ? `${(value * 100).toFixed(1)}%` : 'N/A')

watch(selectedNode, async (node) => {
  await loadProtectedPreview(node)
})

onMounted(async () => {
  await loadGroups()
  const queryGroupId = route.query.groupId
  if (queryGroupId) {
    const targetNode = treeData.value.find((node) => node.id === `group-${queryGroupId}`)
    if (targetNode) {
      selectedNode.value = targetNode
      treeRef.value?.setCurrentKey(targetNode.id)
      try {
        await ensureGroupChildrenLoaded(targetNode)
      } catch (error) {
        handleApiError(error, '加载图像组结构失败')
      }
    }
  }
})

onBeforeUnmount(() => {
  revokePreview()
})
</script>

<style scoped lang="scss">
.detail-page {
  padding: 20px;
  background: #f5f0e8;
  min-height: 100vh;
}

.detail-header {
  margin-bottom: 20px;

  h2 {
    font-size: 24px;
    color: #333;
    margin-bottom: 8px;
  }

  p {
    color: #999;
    font-size: 14px;
  }
}

.detail-container {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 20px;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.tree-panel {
  border-right: 1px solid #eee;
  padding: 20px;
  overflow-y: auto;
  max-height: calc(100vh - 200px);
}

.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;

  h3 {
    font-size: 14px;
    color: #333;
    margin: 0;
  }
}

.tree-content :deep(.el-tree-node__content) {
  height: 32px;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;

  .node-icon {
    color: #409eff;
    font-size: 16px;
  }

  .node-label {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .node-count {
    color: #999;
    font-size: 12px;
  }
}

.content-panel {
  padding: 30px;
  overflow-y: auto;
  max-height: calc(100vh - 200px);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 20px;

  h3 {
    font-size: 18px;
    color: #333;
    margin: 0;
  }
}

.image-preview {
  margin: 20px 0;
  text-align: center;

  img {
    max-width: 100%;
    max-height: 420px;
    border-radius: 8px;
    border: 1px solid #eee;
  }
}

.no-image {
  color: #999;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(140px, 200px));
  gap: 16px;
  margin: 24px 0;
}

.stat-card {
  padding: 20px;
  background: #fafafa;
  border-radius: 8px;
  text-align: center;

  .stat-value {
    font-size: 28px;
    font-weight: 700;
    color: #409eff;
  }

  .stat-label {
    margin-top: 8px;
    color: #666;
    font-size: 14px;
  }
}

.metadata-form {
  margin-top: 20px;
  max-width: 720px;
}

.action-buttons {
  margin-top: 24px;
  display: flex;
  gap: 12px;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 500px;
}
</style>
