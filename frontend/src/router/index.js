import { createRouter, createWebHistory } from 'vue-router'
import StyleTransfer from '@/views/StyleTransfer.vue'
import StyleTraining from '@/views/StyleTraining.vue'
import Evaluation from '@/views/Evaluation.vue'
import StyleManagement from '@/views/StyleManagement.vue'
import LLMConfig from '@/views/LLMConfig.vue'

const routes = [
  {
    path: '/',
    redirect: '/style-transfer'
  },
  {
    path: '/style-transfer',
    name: 'StyleTransfer',
    component: StyleTransfer,
    meta: { title: '风格转化', icon: 'ChatLineRound' }
  },
  {
    path: '/style-training',
    name: 'StyleTraining',
    component: StyleTraining,
    meta: { title: '风格迁移模型训练', icon: 'Cpu' }
  },
  {
    path: '/evaluation',
    name: 'Evaluation',
    component: Evaluation,
    meta: { title: '生成结果可视化', icon: 'TrendCharts' }
  },
  {
    path: '/style-management',
    name: 'StyleManagement',
    component: StyleManagement,
    meta: { title: '风格管理', icon: 'Collection' }
  },
  {
    path: '/config',
    name: 'LLMConfig',
    component: LLMConfig,
    meta: { title: '系统配置', icon: 'Setting' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
