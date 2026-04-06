<template>
  <div class="detail-page">
    <div class="detail-header">
      <h2>简牍图像展示和管理</h2>
      <p>多层级展示：图像组 → 原始图像 → 单支 → 单字</p>
    </div>

    <div class="detail-container">
      <!-- 左侧：树形导航 -->
      <div class="tree-panel">
        <div class="tree-header">
          <h3>图像组织结构</h3>
          <el-button type="primary" size="small" @click="loadGroups">
            刷新
          </el-button>
        </div>
        <el-tree
          ref="treeRef"
          :data="treeData"
          :props="treeProps"
          :expand-on-click-node="false"
          @node-click="handleNodeClick"
          node-key="id"
          class="tree-content"
        >
          <template #default="{ node, data }">
            <div class="tree-node">
              <el-icon v-if="data.type === 'group'" class="node-icon">
                <FolderOpened />
              </el-icon>
              <el-icon v-else-if="data.type === 'images-folder'" class="node-icon">
                <FolderOpened />
              </el-icon>
              <el-icon v-else-if="data.type === 'slips-root-folder'" class="node-icon">
                <FolderOpened />
              </el-icon>
              <el-icon v-else-if="data.type === 'slip-folder'" class="node-icon">
                <Folder />
              </el-icon>
              <el-icon v-else-if="data.type === 'slip-chars-placeholder'" class="node-icon">
                <Folder />
              </el-icon>
              <el-icon v-else-if="data.type === 'image'" class="node-icon">
                <Picture />
              </el-icon>
              <el-icon v-else-if="data.type === 'slip'" class="node-icon">
                <DocumentCopy />
              </el-icon>
              <el-icon v-else class="node-icon">
                <Document />
              </el-icon>
              <span class="node-label">{{ node.label }}</span>
              <span v-if="data.count" class="node-count">({{ data.count }})</span>
            </div>
          </template>
        </el-tree>
      </div>

      <!-- 右侧：内容展示 -->
      <div class="content-panel">
        <!-- 组级别 -->
        <div v-if="selectedNode && selectedNode.type === 'group'" class="content-section">
          <div class="section-header">
            <h3>{{ selectedNode.name }}</h3>
            <el-tag>图像组</el-tag>
          </div>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="组名">{{ selectedNode.name }}</el-descriptions-item>
            <el-descriptions-item label="来源">{{ selectedNode.source_site }}</el-descriptions-item>
            <el-descriptions-item label="时期">{{ selectedNode.period }}</el-descriptions-item>
            <el-descriptions-item label="材质">{{ selectedNode.material }}</el-descriptions-item>
            <el-descriptions-item label="收藏">{{ selectedNode.collection }}</el-descriptions-item>
            <el-descriptions-item label="出土年份">{{ selectedNode.excavation_year }}</el-descriptions-item>
            <el-descriptions-item label="批号">{{ selectedNode.batch_no }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag>{{ getStatusLabel(selectedNode.status) }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-value">{{ selectedNode.total_images }}</div>
              <div class="stat-label">原始图像</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{{ selectedNode.processed_images }}</div>
              <div class="stat-label">已处理</div>
            </div>
          </div>

          <div class="action-buttons">
            <el-button type="primary" @click="handleExportGroup">导出数据</el-button>
            <el-button @click="handleEditGroup">编辑信息</el-button>
          </div>
        </div>

        <!-- 原始图像级别 -->
        <div v-else-if="selectedNode && selectedNode.type === 'image'" class="content-section">
          <div class="section-header">
            <h3>{{ selectedNode.filename }}</h3>
            <el-tag>原始图像</el-tag>
          </div>
          <div class="image-preview">
            <img :src="getFullUrl(selectedNode.url)" :alt="selectedNode.filename" />
          </div>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="文件名">{{ selectedNode.filename }}</el-descriptions-item>
            <el-descriptions-item label="尺寸">{{ selectedNode.width }} × {{ selectedNode.height }}</el-descriptions-item>
            <el-descriptions-item label="格式">{{ selectedNode.format }}</el-descriptions-item>
            <el-descriptions-item label="大小">{{ formatFileSize(selectedNode.file_size) }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 单支文件夹级别 -->
        <div v-else-if="selectedNode && selectedNode.type === 'slip-folder'" class="content-section">
          <div class="section-header">
            <h3>{{ selectedNode.name }}</h3>
            <el-tag type="success">单支</el-tag>
          </div>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="ID">{{ selectedNode.segment_id }}</el-descriptions-item>
            <el-descriptions-item label="置信度">{{ selectedNode.confidence ? (selectedNode.confidence * 100).toFixed(1) + '%' : 'N/A' }}</el-descriptions-item>
            <el-descriptions-item label="尺寸">{{ selectedNode.width }} × {{ selectedNode.height }}</el-descriptions-item>
            <el-descriptions-item label="校验状态">{{ selectedNode.validated ? '已校验' : '未校验' }}</el-descriptions-item>
          </el-descriptions>

          <h4>元数据标注</h4>
          <el-form :model="slipMetadataForm" label-width="120px" class="metadata-form">
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

        <!-- 单支裁剪图 -->
        <div v-else-if="selectedNode && selectedNode.type === 'slip-crop'" class="content-section">
          <div class="section-header">
            <h3>单支裁剪图</h3>
            <el-tag type="info">裁剪图像</el-tag>
          </div>
          <div v-if="selectedNode.storage_path" class="image-preview">
            <img :src="getFullUrl(selectedNode.storage_path)" :alt="selectedNode.name" />
          </div>
          <p v-else class="no-image">暂无裁剪图</p>
        </div>

        <!-- 单支级别 -->
        <div v-else-if="selectedNode && selectedNode.type === 'slip'" class="content-section">
          <div class="section-header">
            <h3>{{ selectedNode.name }}</h3>
            <el-tag type="success">单支</el-tag>
          </div>

          <!-- 单支裁剪图预览 -->
          <div class="image-preview" v-if="selectedNode.url">
            <img :src="selectedNode.url" :alt="selectedNode.name" @error="e => e.target.style.display='none'" />
          </div>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="ID">{{ selectedNode.segment_id }}</el-descriptions-item>
            <el-descriptions-item label="置信度">{{ selectedNode.confidence ? (selectedNode.confidence * 100).toFixed(1) + '%' : 'N/A' }}</el-descriptions-item>
            <el-descriptions-item label="尺寸">{{ selectedNode.width }} × {{ selectedNode.height }}</el-descriptions-item>
            <el-descriptions-item label="校验状态">{{ selectedNode.validated ? '已校验' : '未校验' }}</el-descriptions-item>
          </el-descriptions>

          <h4>元数据标注</h4>
          <el-form :model="slipMetadataForm" label-width="120px" class="metadata-form">
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

        <!-- 单字级别 -->
        <div v-else-if="selectedNode && selectedNode.type === 'char'" class="content-section">
          <div class="section-header">
            <h3>{{ selectedNode.name }}</h3>
            <el-tag type="warning">单字</el-tag>
          </div>

          <!-- 单字裁剪图预览 -->
          <div class="image-preview" v-if="selectedNode.url">
            <img :src="selectedNode.url" :alt="selectedNode.name" @error="e => e.target.style.display='none'" />
          </div>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="ID">{{ selectedNode.segment_id }}</el-descriptions-item>
            <el-descriptions-item label="置信度">{{ selectedNode.confidence ? (selectedNode.confidence * 100).toFixed(1) + '%' : 'N/A' }}</el-descriptions-item>
            <el-descriptions-item label="尺寸">{{ selectedNode.width }} × {{ selectedNode.height }}</el-descriptions-item>
            <el-descriptions-item label="校验状态">{{ selectedNode.validated ? '已校验' : '未校验' }}</el-descriptions-item>
          </el-descriptions>

          <h4>元数据标注</h4>
          <el-form :model="charMetadataForm" label-width="120px" class="metadata-form">
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

        <!-- 空状态 -->
        <div v-else class="empty-state">
          <el-empty description="请从左侧选择要查看的内容" />
        </div>
      </div>
    </div>

    <!-- 编辑图像组对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑图像组信息" width="500px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="组名称"><el-input v-model="editForm.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="editForm.description" type="textarea" /></el-form-item>
        <el-form-item label="出土地点"><el-input v-model="editForm.source_site" /></el-form-item>
        <el-form-item label="时代断代"><el-input v-model="editForm.period" /></el-form-item>
        <el-form-item label="材质">
          <el-select v-model="editForm.material">
            <el-option label="竹" value="竹" />
            <el-option label="木" value="木" />
          </el-select>
        </el-form-item>
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
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  FolderOpened,
  Folder,
  Picture,
  DocumentCopy,
  Document
} from '@element-plus/icons-vue'
import { groupsAPI } from '@/api/groups'
import { metadataAPI } from '@/api/metadata'
import { handleApiError } from '@/utils/errorHandler'

const API_BASE_URL = import.meta.env.VITE_BACKEND_BASE_URL || 'http://127.0.0.1:8000'

const route = useRoute()
const treeRef = ref(null)
const groups = ref([])
const selectedNode = ref(null)
const treeData = ref([])

// 编辑对话框状态
const showEditDialog = ref(false)
const editForm = ref({
  name: '',
  description: '',
  source_site: '',
  period: '',
  material: '',
  collection: ''
})

// 元数据表单
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
  label: (data) => {
    if (data.type === 'group') return data.name
    if (data.type === 'image') return data.filename
    if (data.type === 'slip-folder') return data.name
    if (data.type === 'slip-crop') return data.name
    if (data.type === 'char') return data.name
    return data.name || data.id
  }
}

const loadGroups = async () => {
  try {
    const data = await groupsAPI.getGroups()
    groups.value = data || []

    // 构建树形数据：新结构 - 组下直接显示原图，单支列表（点击展开）
    treeData.value = groups.value.map(group => ({
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
      count: group.total_images,
      children: [
        // 第一项：原图文件夹（延迟加载原始图像列表）
        {
          id: `images-${group.id}`,
          type: 'images-folder',
          name: '原图',
          count: group.total_images,
          children: []       // 延迟加载
        },
        // 第二项起：单支文件夹占位（延迟加载后按序号展开）
        // 使用一个 slips-root-folder 作为容器，点击时动态生成各 slip 子文件夹
        {
          id: `slips-root-${group.id}`,
          type: 'slips-root-folder',
          name: '单支列表（点击展开）',
          count: 0,
          children: []       // 延迟加载
        }
      ]
    }))
  } catch (error) {
    handleApiError(error, '加载图像组失败')
  }
}

const handleNodeClick = async (data) => {
  // ── group 节点 ──────────────────────────────────────────────────────────
  if (data.type === 'group') {
    selectedNode.value = data
    return
  }

  // ── 原图文件夹（images-folder）──────────────────────────────────────────
  if (data.type === 'images-folder') {
    if (data.children.length === 0) {
      const groupId = data.id.replace('images-', '')
      try {
        const response = await groupsAPI.getGroupImages(groupId)
        const images   = response.items || []
        data.children  = images.map((img, idx) => ({
          id: `image-${img.id}`,
          type: 'image',
          name: img.filename || `原图 ${idx + 1}`,
          filename: img.filename,
          url: img.file_url || img.storage_path,
          width: img.width,
          height: img.height,
          format: img.format,
          file_size: img.file_size,
          group_id: img.group_id,
          source_image_id: img.id
        }))
        treeRef.value.updateKeyChildren(data.id, data.children)
      } catch (error) {
        handleApiError(error, '加载原始图像失败')
      }
    }
    return
  }

  // ── 单支列表占位节点（slips-root-folder）──────────────────────────────
  // 点击后展开，将 group.children 中的占位节点替换为逐个 slip-folder
  if (data.type === 'slips-root-folder') {
    if (data.children.length === 0) {
      const groupId = data.id.replace('slips-root-', '')
      try {
        // 拉取该组全部 slip segments
        const slips = await groupsAPI.getGroupSegments(groupId, { type: 'slip' })

        if (!slips || slips.length === 0) {
          ElMessage.info('该图像组暂无单支数据，请先完成切割与校验')
          return
        }

        // 构建每个 slip 的文件夹节点
        const slipFolders = slips.map((slip, idx) => ({
          id: `slip-folder-${slip.id}`,
          type: 'slip-folder',
          name: `单支 ${idx + 1}`,
          slip_id: slip.id,
          source_image_id: slip.source_image_id,
          group_id: groupId,
          confidence: slip.confidence,
          validated: slip.validated,
          children: [
            // 第一子项：单支图像本身
            {
              id: `slip-self-${slip.id}`,
              type: 'slip',
              name: `单支 ${idx + 1}`,
              segment_id: slip.id,
              source_image_id: slip.source_image_id,
              group_id: groupId,
              width: slip.bbox_width,
              height: slip.bbox_height,
              confidence: slip.confidence,
              validated: slip.validated,
              // 拼接文件预览 URL
              url: `${API_BASE_URL}/api/groups/${groupId}/segments/${slip.id}/file`,
            },
            // 后续子项：该 slip 的单字（延迟加载占位）
            {
              id: `chars-of-${slip.id}`,
              type: 'slip-chars-placeholder',
              name: '单字（点击加载）',
              slip_id: slip.id,
              group_id: groupId,
              children: []
            }
          ]
        }))

        // 找到 group 节点，将 slips-root-folder 替换为各个 slip-folder
        const groupNode = treeData.value.find(n => n.id === `group-${groupId}`)
        if (groupNode) {
          // 移除占位节点，追加 slip 文件夹列表
          groupNode.children = groupNode.children.filter(
            c => c.type !== 'slips-root-folder'
          )
          groupNode.children.push(...slipFolders)
          treeRef.value.updateKeyChildren(`group-${groupId}`, groupNode.children)
        }

      } catch (error) {
        handleApiError(error, '加载单支列表失败')
      }
    }
    return
  }

  // ── slip-folder（单支文件夹，展示子内容，不直接展示内容面板）──────────
  if (data.type === 'slip-folder') {
    // 仅展开，不需要设置 selectedNode（文件夹本身不展示内容）
    // 子节点 slip-chars-placeholder 负责延迟加载单字
    return
  }

  // ── slip-chars-placeholder（单字列表占位）────────────────────────────
  if (data.type === 'slip-chars-placeholder') {
    if (data.children.length === 0) {
      const { slip_id, group_id } = data
      try {
        // 获取该 slip 的所有单字 segments（通过后端 parent_segment_id 过滤）
        const chars = await groupsAPI.getGroupSegments(group_id, {
          type: 'char',
          parentSegmentId: slip_id   // 直接后端过滤，无需前端 filter
        })

        data.children = (chars || []).map((char, idx) => ({
          id: `char-${char.id}`,
          type: 'char',
          name: `单字 ${idx + 1}`,
          segment_id: char.id,
          source_image_id: char.source_image_id,
          parent_segment_id: slip_id,
          group_id: group_id,
          width: char.bbox_width,
          height: char.bbox_height,
          confidence: char.confidence,
          validated: char.validated,
          url: `${API_BASE_URL}/api/groups/${group_id}/segments/${char.id}/file`,
        }))
        treeRef.value.updateKeyChildren(data.id, data.children)
      } catch (error) {
        handleApiError(error, '加载单字失败')
      }
    }
    return
  }

  // ── 叶节点（image / slip / char）─────────────────────────────────────
  if (['image', 'slip', 'char'].includes(data.type)) {
    selectedNode.value = data
    return
  }
}

const handleExportGroup = async () => {
  if (!selectedNode.value || selectedNode.value.type !== 'group') return
  const groupId = selectedNode.value.id.replace('group-', '')

  try {
    const result = await ElMessageBox.confirm(
      '选择导出格式',
      '导出数据',
      {
        distinguishCancelAndClose: true,
        confirmButtonText: 'MSJ 格式',
        cancelButtonText: 'COCO 格式'
      }
    )
    const format = result === 'confirm' ? 'msj' : 'coco'

    const response = await groupsAPI.exportGroup(groupId, { format, include_images: true })
    ElMessage.success(`导出成功，格式: ${format}`)

    if (response.file_url) {
      window.open(`${API_BASE_URL}${response.file_url}`, '_blank')
    }
  } catch (e) {
    if (e !== 'cancel') handleApiError(e, '导出失败')
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
  if (!selectedNode.value) return
  const groupId = selectedNode.value.id.replace('group-', '')
  try {
    await groupsAPI.updateGroup(groupId, editForm.value)
    Object.assign(selectedNode.value, editForm.value)
    showEditDialog.value = false
    ElMessage.success('已保存')
    await loadGroups()
  } catch (e) {
    handleApiError(e, '保存失败')
  }
}

const handleSaveMetadata = () => {
  ElMessage.success('元数据已保存')
}

const handleSaveSlipMetadata = async () => {
  if (!selectedNode.value || (selectedNode.value.type !== 'slip' && selectedNode.value.type !== 'slip-folder')) return
  try {
    await metadataAPI.saveSegmentMetadata(selectedNode.value.segment_id, {
      title: slipMetadataForm.value.slip_id,
      content_description: slipMetadataForm.value.content_text,
      event_type: slipMetadataForm.value.condition,
      extra: JSON.stringify({ notes: slipMetadataForm.value.notes })
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
      extra: JSON.stringify({ confidence_override: charMetadataForm.value.confidence_override })
    })
    ElMessage.success('单字元数据已保存')
  } catch (error) {
    handleApiError(error, '保存元数据失败')
  }
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

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const getFullUrl = (path) => {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  return `${API_BASE_URL}${path}`
}

onMounted(async () => {
  await loadGroups()

  // 从 query 预选组
  const queryGroupId = route.query.groupId
  if (queryGroupId && treeRef.value) {
    const targetNode = treeData.value.find(n => n.id === `group-${queryGroupId}`)
    if (targetNode) {
      selectedNode.value = targetNode
      treeRef.value.setCurrentKey(targetNode.id)
    }
  }
})
</script>

<style scoped lang="scss">
.detail-page {
  padding: 20px;
  background: #F5F0E8;
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

  .tree-content {
    :deep(.el-tree-node__content) {
      height: 32px;
    }
  }
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;

  .node-icon {
    color: #409EFF;
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

.content-section {
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
      max-height: 400px;
      border-radius: 8px;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    }
  }

  :deep(.el-descriptions) {
    margin: 20px 0;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 15px;
    margin: 20px 0;

    .stat-card {
      padding: 20px;
      background: #f5f7fa;
      border-radius: 8px;
      text-align: center;

      .stat-value {
        font-size: 28px;
        font-weight: bold;
        color: #409EFF;
      }

      .stat-label {
        font-size: 14px;
        color: #999;
        margin-top: 8px;
      }
    }
  }

  .metadata-form {
    max-width: 600px;
    margin: 20px 0;

    h4 {
      margin: 20px 0 15px 0;
      font-size: 16px;
      color: #333;
    }
  }

  .action-buttons {
    display: flex;
    gap: 10px;
    margin-top: 20px;
  }
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
}

@media (max-width: 768px) {
  .detail-container {
    grid-template-columns: 1fr;
  }

  .tree-panel {
    border-right: none;
    border-bottom: 1px solid #eee;
    max-height: 300px;
  }
}
</style>
