<template>
  <div class="auth-page auth-page--register">
    <div class="auth-container auth-container--register">
      <el-card class="auth-frame auth-frame--horizontal" shadow="never" :body-style="{ padding: '0' }">
        <section class="auth-hero">
          <div class="auth-hero__badge">创建账户 · 邮箱验证</div>
          <div class="auth-hero__title">加入研究流程</div>
          <div class="auth-hero__desc">
            创建云端账户后，你的操作与状态将与后端服务绑定，可进行鉴权测试与受保护接口调用。
          </div>
          <div class="auth-hero__meta">注册后需要完成邮箱验证，才能正常登录</div>
        </section>

        <section class="auth-panel">
          <div class="auth-panel__header">
            <div class="auth-panel__title">注册</div>
            <div class="auth-panel__subtitle">使用邮箱与密码创建账户</div>
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
                autocomplete="new-password"
              />
            </el-form-item>

            <div class="auth-panel__actions">
              <el-button class="auth-panel__primary" type="primary" :loading="loading" @click="handleRegister">
                注册
              </el-button>
              <el-button text @click="goLogin">返回登录</el-button>
            </div>
          </el-form>

          <div class="auth-panel__hint">注册成功后需要邮箱验证，请按提示完成验证。</div>

          <div v-if="registeredEmail" class="auth-panel__aux">
            <div class="auth-panel__aux-text">未收到邮件？可尝试重发验证邮件（注意检查垃圾箱）。</div>
            <el-button size="small" :loading="resendLoading" @click="resendVerification">重发验证邮件</el-button>
          </div>
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

const router = useRouter()

const formRef = ref(null)
const loading = ref(false)
const resendLoading = ref(false)
const registeredEmail = ref('')

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

const handleRegister = async () => {
  if (loading.value) return

  const ok = await formRef.value?.validate?.().catch(() => false)
  if (!ok) return

  loading.value = true
  try {
    const email = String(form.email || '').trim().toLowerCase()
    const password = String(form.password || '')

    const { data, error } = await supabase.auth.signUp({
      email,
      password
    })

    if (error) {
      handleApiError(error, '注册失败')
    } else {
      ElMessage.success('注册成功，请检查邮箱验证')
      registeredEmail.value = email
      if (data?.user) {
        router.push('/login')
      }
    }
  } catch (e) {
    handleApiError(e, '注册失败')
  } finally {
    loading.value = false
  }
}

const resendVerification = async () => {
  if (resendLoading.value) return
  const email = String(registeredEmail.value || '').trim().toLowerCase()
  if (!email) return

  resendLoading.value = true
  try {
    const { error } = await supabase.auth.resend({
      type: 'signup',
      email
    })
    if (error) {
      handleApiError(error, '重发验证邮件失败')
    } else {
      ElMessage.success('已重新发送验证邮件，请检查邮箱')
    }
  } catch (e) {
    handleApiError(e, '重发验证邮件失败')
  } finally {
    resendLoading.value = false
  }
}

const goLogin = () => {
  router.push('/login')
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
  max-width: 980px;
}

.auth-frame {
  border-radius: 18px;
  border: 1px solid rgba(31, 45, 61, 0.10);
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 18px 46px rgba(17, 24, 39, 0.10);
  overflow: hidden;
}

.auth-frame--horizontal :deep(.el-card__body) {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
}

.auth-hero {
  padding: 34px 30px;
  background:
    radial-gradient(1200px 520px at 20% -20%, rgba(22, 163, 156, 0.24) 0%, rgba(22, 163, 156, 0) 55%),
    radial-gradient(900px 480px at 100% 10%, rgba(37, 99, 235, 0.16) 0%, rgba(37, 99, 235, 0) 55%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.80) 0%, rgba(255, 255, 255, 0.92) 100%);
  border-right: 1px solid rgba(31, 45, 61, 0.08);
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
  margin-top: 14px;
  font-size: 22px;
  font-weight: 950;
  color: #1f2d3d;
  letter-spacing: 0.6px;
}

.auth-hero__desc {
  margin-top: 10px;
  font-size: 13px;
  line-height: 1.8;
  color: rgba(31, 45, 61, 0.70);
}

.auth-hero__meta {
  margin-top: 12px;
  font-size: 12px;
  color: rgba(31, 45, 61, 0.55);
  line-height: 1.6;
}

.auth-panel {
  padding: 26px 26px 22px;
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
  line-height: 1.6;
}

.auth-panel__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
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

.auth-panel__aux {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.auth-panel__aux-text {
  font-size: 12px;
  color: rgba(31, 45, 61, 0.55);
  line-height: 1.6;
}

@media (max-width: 860px) {
  .auth-container {
    max-width: 520px;
  }

  .auth-frame--horizontal :deep(.el-card__body) {
    grid-template-columns: 1fr;
  }

  .auth-hero {
    border-right: none;
    border-bottom: 1px solid rgba(31, 45, 61, 0.08);
    padding: 26px 20px 22px;
  }

  .auth-panel {
    padding: 20px 20px 18px;
  }
}
</style>
