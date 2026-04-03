<template>
  <div class="auth-page auth-page--login">
    <div class="auth-container auth-container--login">
      <el-card class="auth-frame auth-frame--vertical" shadow="never" :body-style="{ padding: '0' }">
        <section class="auth-hero">
          <div class="auth-hero__badge">云端账户 · 安全登录</div>
          <div class="auth-hero__title">基于云存储的简牍图片切割及管理系统的设计与实现</div>
          <div class="auth-hero__desc">
            以科研流程为导向，支持图像管理、元数据整理与统计分析。登录后可使用鉴权接口与后端能力。
          </div>
          <div class="auth-hero__meta">建议使用已完成邮箱验证的账号登录</div>
        </section>

        <section class="auth-panel">
          <div class="auth-panel__header">
            <div class="auth-panel__title">登录</div>
            <div class="auth-panel__subtitle">使用邮箱与密码进入系统</div>
          </div>

          <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="form.email" placeholder="请输入邮箱" autocomplete="email" />
            </el-form-item>

            <el-form-item label="密码" prop="password">
              <el-input
                v-model="form.password"
                type="password"
                show-password
                placeholder="请输入密码"
                autocomplete="current-password"
              />
            </el-form-item>

            <div class="auth-panel__actions">
              <el-button class="auth-panel__primary" type="primary" :loading="loading" @click="handleLogin">
                登录
              </el-button>
              <el-button text @click="goRegister">去注册</el-button>
            </div>
          </el-form>

          <div class="auth-panel__hint">默认连接 Supabase Auth；如未配置环境变量，请先检查根目录 `.env`。</div>
        </section>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { handleApiError } from '@/utils/errorHandler'
import { useRouter } from 'vue-router'

import { supabase } from '@/lib/supabase'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const router = useRouter()

const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  email: '',
  password: ''
})

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  if (loading.value) return

  const ok = await formRef.value?.validate?.().catch(() => false)
  if (!ok) return

  loading.value = true
  try {
    const email = String(form.email || '').trim().toLowerCase()
    const password = String(form.password || '')

    console.log("[Login] Signing in with:", form.email);     const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password
    })

    if (error) {
      const extra =
        error.message === 'Invalid login credentials'
          ? '（可能原因：邮箱未验证 / 邮箱或密码输入有误 / 注册未成功）'
          : ''
      handleApiError(error, `登录失败${extra}`)
    } else {
      console.log("[Login] Session received:", { hasSession: !!data.session, accessToken: data.session?.access_token ? "***" : "none" });       userStore.setSession(data.session);       console.log("[Login] localStorage after set:", !!localStorage.getItem("sb-pfqrvhqwrgijrjcbeea-auth-token"));
      ElMessage.success('登录成功')
      router.push('/')
    }
  } catch (e) {
    handleApiError(e, '登录失败')
  } finally {
    loading.value = false
  }
}

const goRegister = () => {
  router.push('/register')
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 42px 16px;
  background: linear-gradient(180deg, #f3f1ea 0%, #f6f7f8 55%, #f5f7fa 100%);
}

.auth-container {
  width: 100%;
  max-width: 520px;
}

.auth-frame {
  border-radius: 16px;
  border: 1px solid rgba(31, 45, 61, 0.10);
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 16px 36px rgba(17, 24, 39, 0.08);
  overflow: hidden;
}

.auth-hero {
  padding: 26px 24px 22px;
  background:
    radial-gradient(1200px 420px at 20% -20%, rgba(22, 163, 156, 0.22) 0%, rgba(22, 163, 156, 0) 55%),
    radial-gradient(900px 380px at 90% 0%, rgba(37, 99, 235, 0.14) 0%, rgba(37, 99, 235, 0) 50%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.80) 0%, rgba(255, 255, 255, 0.92) 100%);
  border-bottom: 1px solid rgba(31, 45, 61, 0.08);
}

.auth-hero__badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: rgba(31, 45, 61, 0.75);
  background: rgba(255, 255, 255, 0.70);
  border: 1px solid rgba(31, 45, 61, 0.10);
}

.auth-hero__title {
  margin-top: 12px;
  font-size: 20px;
  font-weight: 900;
  color: #1f2d3d;
  letter-spacing: 0.6px;
}

.auth-hero__desc {
  margin-top: 10px;
  font-size: 13px;
  line-height: 1.75;
  color: rgba(31, 45, 61, 0.70);
}

.auth-hero__meta {
  margin-top: 10px;
  font-size: 12px;
  color: rgba(31, 45, 61, 0.55);
}

.auth-panel {
  padding: 20px 24px 22px;
  background: rgba(255, 255, 255, 0.98);
}

.auth-panel__header {
  margin-bottom: 12px;
}

.auth-panel__title {
  font-size: 18px;
  font-weight: 900;
  color: #1f2d3d;
  letter-spacing: 0.4px;
}

.auth-panel__subtitle {
  margin-top: 6px;
  font-size: 12px;
  color: rgba(31, 45, 61, 0.55);
}

.auth-panel__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 10px;
}

.auth-panel__primary {
  flex: 1;
  border-radius: 10px;
}

.auth-panel__hint {
  margin-top: 14px;
  font-size: 12px;
  color: rgba(31, 45, 61, 0.55);
  line-height: 1.6;
}

@media (max-width: 520px) {
  .auth-container {
    max-width: 420px;
  }

  .auth-hero {
    padding: 22px 16px 18px;
  }

  .auth-panel {
    padding: 18px 16px 18px;
  }
}
</style>
