<template>
  <section class="page page--placeholder">
    <div class="placeholder-content">
      <el-icon class="placeholder-icon" :size="64"><Document /></el-icon>
      <h2>标注与释读</h2>
      <p class="placeholder-text">功能开发中，敬请期待...</p>
      <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
    </div>
  </section>
</template>

<script setup>
import { Document } from '@element-plus/icons-vue'
</script>

<style scoped>
.page--placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 56px - 36px);
}

.placeholder-content {
  text-align: center;
  padding: 40px 20px;
}

.placeholder-icon {
  color: var(--text-secondary);
  opacity: 0.5;
}

.placeholder-text {
  color: var(--text-secondary);
  font-size: var(--text-base);
  margin-bottom: 24px;
}
</style>
