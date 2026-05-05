import { createRouter, createWebHistory } from 'vue-router'

import Layout from '@/layout/Layout.vue'
import pinia from '@/store'
import { useUserStore } from '@/store/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue')
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue')
  },
  {
    path: '/testPage',
    name: 'TestPage',
    meta: { title: '核心功能测试页面', requiresAuth: false },
    component: () => import('@/views/TestPage.vue')
  },
  {
    path: '/',
    component: Layout,
    children: [
      {
        path: '',
        name: 'StartPage',
        component: () => import('@/views/StartPage.vue')
      },
      {
        path: 'groups',
        name: 'ImageGroups',
        meta: { title: '图像组管理' },
        component: () => import('@/views/ImageGroupView.vue')
      },
      {
        path: 'segmentation',
        name: 'Segmentation',
        meta: { title: '图像切割' },
        component: () => import('@/views/Segmentation.vue')
      },
      {
        path: 'batch-segmentation',
        name: 'BatchSegmentation',
        meta: { title: '批量切割' },
        component: () => import('@/views/BatchSegmentation.vue')
      },
      {
        path: 'batch/verify/:groupId/:stage',
        name: 'BatchVerification',
        meta: { title: '批量校验' },
        component: () => import('@/views/BatchVerificationView.vue')
      },
      {
        path: 'preprocess',
        name: 'Preprocess',
        meta: { title: '图像预处理' },
        component: () => import('@/views/preprocess/PreprocessPipeline.vue')
      },
      {
        path: 'metadata',
        name: 'Metadata',
        meta: { title: '图像元数据管理' },
        component: () => import('@/views/Metadata.vue')
      },
      {
        path: 'recognition',
        name: 'Recognition',
        meta: { title: '图像预处理（旋转与归一化）' },
        component: () => import('@/views/Recognition.vue')
      },
      {
        path: 'recognition/verify/:groupId/:stage',
        name: 'RecognitionVerify',
        meta: { title: '校验视图' },
        component: () => import('@/views/RecognitionVerifyView.vue')
      },
      {
        path: 'annotation',
        name: 'Annotation',
        meta: { title: '标注与释读' },
        component: () => import('@/views/Annotation.vue')
      },
      {
        path: 'detail',
        name: 'Detail',
        meta: { title: '简牍图像展示和管理' },
        component: () => import('@/views/Detail.vue')
      },
      {
        path: 'slip-gallery',
        name: 'SlipGallery',
        meta: { title: '简牍图库' },
        component: () => import('@/views/SlipGallery.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const userStore = useUserStore(pinia)

  // 测试页面无需鉴权
  if (to.path === '/testPage') {
    return true
  }

  if (!userStore.user && to.path !== '/login' && to.path !== '/register') {
    return '/login'
  }

  if (userStore.user && (to.path === '/login' || to.path === '/register')) {
    return '/'
  }
})

export default router
