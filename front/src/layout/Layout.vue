<template>
  <el-container class="layout" direction="vertical">
    <el-header class="layout__header" height="56px">
      <HeaderBar />
    </el-header>

    <el-container class="layout__body">
      <el-aside class="layout__aside" :width="sidebarWidth">
        <Sidebar />
      </el-aside>

      <el-main class="layout__content">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { RouterView } from 'vue-router'
import Sidebar from './components/Sidebar.vue'
import HeaderBar from './components/HeaderBar.vue'

// Responsive sidebar width
const sidebarWidth = computed(() => {
  // Check if window is available (SSR safety)
  if (typeof window === 'undefined') return '240px'
  const width = window.innerWidth
  // On mobile screens, use a smaller sidebar or hide it
  if (width < 768) return '64px'
  return '240px'
})
</script>

<style scoped>
.layout {
  height: 100vh;
  background: var(--app-bg);
}

.layout__body {
  min-height: 0;
}

.layout__aside {
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border-color);
  transition: width var(--transition-base);
}

.layout__header {
  background: var(--header-bg);
  border-bottom: 1px solid var(--border-color);
  padding: 0;
}

.layout__content {
  padding: 18px 20px;
  overflow: auto;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .layout__content {
    padding: 12px;
  }
}

@media (max-width: 576px) {
  .layout__content {
    padding: 8px;
  }
}
</style>
