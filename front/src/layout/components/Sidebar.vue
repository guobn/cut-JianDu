<template>
  <div class="sidebar" :class="{ 'sidebar--collapsed': isCollapsed }">
    <el-menu
      class="sidebar__menu"
      :default-active="activeMenu"
      :router="true"
      :collapse="isCollapsed"
      background-color="transparent"
      text-color="var(--sidebar-text)"
      active-text-color="var(--sidebar-active)"
      :collapse-transition="false"
    >
      <div v-if="!isCollapsed" class="sidebar__group">核心功能</div>

      <el-menu-item index="/preprocess">
        <el-icon><MagicStick /></el-icon>
        <span>图像预处理</span>
      </el-menu-item>

      <el-menu-item index="/groups">
        <el-icon><FolderOpened /></el-icon>
        <span>图像组管理</span>
      </el-menu-item>

      <el-menu-item index="/segmentation">
        <el-icon><Scissor /></el-icon>
        <span>图像切割</span>
      </el-menu-item>

      <el-menu-item index="/batch-segmentation">
        <el-icon><Scissor /></el-icon>
        <span>批量切割</span>
      </el-menu-item>

      <el-menu-item index="/recognition">
        <el-icon><EditPen /></el-icon>
        <span>旧版预处理</span>
      </el-menu-item>

      <el-menu-item index="/metadata">
        <el-icon><Files /></el-icon>
        <span>元数据管理</span>
      </el-menu-item>

      <el-menu-item index="/detail">
        <el-icon><View /></el-icon>
        <span>简牍图像详情</span>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  EditPen,
  Files,
  FolderOpened,
  MagicStick,
  Scissor,
  View
} from '@element-plus/icons-vue'

const route = useRoute()

const activeMenu = computed(() => route.path)

const isCollapsed = computed(() => {
  if (typeof window === 'undefined') return false
  return window.innerWidth < 768
})
</script>

<style scoped>
.sidebar {
  height: 100%;
  display: flex;
  flex-direction: column;
  transition: width var(--transition-base);
}

.sidebar--collapsed .sidebar__group {
  display: none;
}

.sidebar__group {
  padding: 14px 14px 8px;
  font-size: 12px;
  color: rgba(31, 45, 61, 0.55);
  white-space: nowrap;
  overflow: hidden;
}

.sidebar__menu {
  flex: 1;
  border-right: none;
  padding: 12px 10px 12px;
}

.sidebar--collapsed .sidebar__menu {
  padding: 12px 4px;
}

:deep(.el-menu-item) {
  height: 42px;
  line-height: 42px;
  border-radius: 10px;
  margin: 4px 0;
}

:deep(.el-menu-item:hover) {
  background-color: var(--sidebar-hover-bg);
}

:deep(.el-menu-item.is-active) {
  background-color: var(--sidebar-active-bg);
}

:deep(.sidebar--collapsed .el-menu-item) {
  margin: 4px 2px;
  justify-content: center;
}
</style>
