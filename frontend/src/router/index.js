import { createRouter, createWebHistory } from 'vue-router'
import StyleTransfer from '@/views/StyleTransfer.vue'
import StyleTraining from '@/views/StyleTraining.vue'
import Evaluation from '@/views/Evaluation.vue'
import StyleManagement from '@/views/StyleManagement.vue'
import SystemMonitoring from '@/views/SystemMonitoring.vue'
import Explore from '@/views/Explore.vue'

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
    meta: { title: '模型训练', icon: 'Cpu' }
  },
  {
    path: '/evaluation',
    name: 'Evaluation',
    component: Evaluation,
    meta: { title: '结果评估', icon: 'TrendCharts' }
  },
  {
    path: '/style-management',
    name: 'StyleManagement',
    component: StyleManagement,
    meta: { title: '风格管理', icon: 'Collection', isManagement: true }
  },
  {
    path: '/system-monitoring',
    name: 'SystemMonitoring',
    component: SystemMonitoring,
    meta: { title: '系统监控', icon: 'Monitor', isManagement: true }
  },
  {
    path: '/explore',
    name: 'Explore',
    component: Explore,
    meta: { title: '探索', icon: 'Compass' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
