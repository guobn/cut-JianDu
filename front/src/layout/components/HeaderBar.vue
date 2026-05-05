<template>
  <div class="header">
    <div class="header__left">
      <div class="header__logo" role="img" aria-label="系统 Logo">
        <el-icon :size="18"><Memo /></el-icon>
      </div>
      <div class="header__brand">
        <div class="header__brand-title">基于云存储的简牍图片切割及管理系统</div>
        <div class="header__brand-subtitle">Ancient Script Analysis System</div>
      </div>
    </div>

    <div class="header__right">
      <button
        class="header__icon-btn"
        type="button"
        @click="noop"
        aria-label="通知"
        title="通知"
      >
        <el-icon :size="18"><Bell /></el-icon>
      </button>
      <button
        class="header__icon-btn"
        type="button"
        @click="noop"
        aria-label="帮助"
        title="帮助"
      >
        <el-icon :size="18"><QuestionFilled /></el-icon>
      </button>

      <div class="header__user" role="button" tabindex="0" aria-label="用户菜单">
        <el-avatar :size="30" class="header__avatar">研</el-avatar>
        <div class="header__user-meta">
          <div class="header__user-name">张研究员</div>
          <div class="header__user-role">研究员</div>
        </div>
        <el-icon class="header__user-arrow" :size="14"><ArrowDown /></el-icon>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ArrowDown, Bell, Memo, QuestionFilled } from '@element-plus/icons-vue'

const noop = () => {}
</script>

<style scoped>
.header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  gap: 12px;
}

.header__left {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 10px;
}

.header__logo {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: rgba(43, 75, 111, 0.12);
  color: #2b4b6f;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.header__brand {
  min-width: 0;
}

.header__brand-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header__brand-subtitle {
  margin-top: 3px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header__right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.header__icon-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: #fff;
  color: #334155;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.header__icon-btn:hover {
  background: rgba(31, 45, 61, 0.03);
}

.header__icon-btn:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

.header__user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border-radius: 10px;
  border: 1px solid var(--border-color);
  background: #fff;
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.header__user:hover {
  background: rgba(31, 45, 61, 0.03);
}

.header__user:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

.header__avatar {
  background: rgba(43, 75, 111, 0.14);
  color: #2b4b6f;
  font-weight: 700;
}

.header__user-meta {
  line-height: 1.1;
}

.header__user-name {
  font-size: 12px;
  font-weight: 700;
  color: #1f2d3d;
}

.header__user-role {
  margin-top: 3px;
  font-size: 11px;
  color: #6b7280;
}

.header__user-arrow {
  color: #64748b;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .header {
    padding: 0 12px;
  }

  .header__brand-title {
    font-size: 12px;
  }

  .header__brand-subtitle {
    display: none;
  }

  .header__user-meta {
    display: none;
  }
}

@media (max-width: 576px) {
  .header__brand {
    display: none;
  }
}
</style>
