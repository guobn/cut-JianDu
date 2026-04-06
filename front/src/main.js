import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'

import { supabase } from '@/lib/supabase'
import pinia from '@/store'
import { useUserStore } from '@/store/user'

import './styles/base.css'

const app = createApp(App)

app.use(pinia)
app.use(router)
app.use(ElementPlus)

// 在 router 就绪后再初始化 session，避免路由守卫时序问题
router.isReady().then(() => {
  supabase.auth.getSession().then(({ data }) => {
    const userStore = useUserStore(pinia)
    userStore.setSession(data.session)
  })

  supabase.auth.onAuthStateChange((_event, session) => {
    const userStore = useUserStore(pinia)
    userStore.setSession(session)
  })
})

app.mount('#app')
