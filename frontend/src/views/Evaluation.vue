<template>
  <div class="evaluation-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-title">
          <div class="title-icon">
            <el-icon :size="28"><DataLine /></el-icon>
          </div>
          <div class="title-text">
            <h1>训练结果评估</h1>
            <p>查看模型训练效果和分析报告</p>
          </div>
        </div>
      </div>
    </div>

    <div class="evaluation-layout">
      <!-- Left Panel: Task Selector -->
      <div class="selector-panel">
        <div class="panel-card">
          <div class="panel-header">
            <el-icon><List /></el-icon>
            <span>选择训练任务</span>
          </div>

          <div class="task-list">
            <div
              v-for="task in completedTasks"
              :key="task.id"
              :class="['task-item', { active: selectedTaskId === task.id }]"
              @click="selectTask(task)"
            >
              <div class="task-status-icon" :class="getStatusClass(task.status)">
                <el-icon v-if="task.status === 'COMPLETED'" :size="16"><Check /></el-icon>
                <el-icon v-else :size="16"><Close /></el-icon>
              </div>

              <div class="task-info">
                <span class="task-name">{{ task.name || '未命名任务' }}</span>
                <span class="task-meta">
                  {{ formatTime(task.completed_at) }} · {{ task.progress }}%
                </span>
              </div>

              <el-icon v-if="selectedTaskId === task.id" class="selected-icon"><ArrowRight /></el-icon>
            </div>

            <div v-if="completedTasks.length === 0" class="empty-tasks">
              <el-icon :size="40" color="#cbd5e1"><Document /></el-icon>
              <p>暂无已完成的任务</p>
              <el-button type="primary" link @click="$router.push('/style-training')">
                去训练模型
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Panel: Evaluation Result -->
      <div class="result-panel">
        <div v-if="selectedTaskId" v-loading="loading" class="result-card">
          <div class="result-header">
            <div class="header-left">
              <h2>{{ currentTask?.name || '评估报告' }}</h2>
              <div class="task-tags">
                <el-tag size="small" type="success" effect="light">
                  <el-icon><Check /></el-icon>
                  已完成
                </el-tag>
                <el-tag size="small" type="info" effect="light">
                  {{ formatDate(currentTask?.completed_at) }}
                </el-tag>
              </div>
            </div>
            <div class="header-actions">
              <el-button :icon="Refresh" circle @click="loadEvaluation" />
              <el-button :icon="Download" circle title="导出报告" />
            </div>
          </div>

          <!-- Quick Stats -->
          <div class="stats-row">
            <div class="stat-card">
              <div class="stat-icon"><el-icon><TrendCharts /></el-icon></div>
              <div class="stat-data">
                <span class="stat-label">最终Loss</span>
                <span class="stat-value">{{ currentTask?.current_loss?.toFixed(4) || '0.1234' }}</span>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon time"><el-icon><Timer /></el-icon></div>
              <div class="stat-data">
                <span class="stat-label">训练时长</span>
                <span class="stat-value">{{ formatDuration(currentTask?.elapsed_time) }}</span>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon epochs"><el-icon><CircleCheck /></el-icon></div>
              <div class="stat-data">
                <span class="stat-label">训练轮数</span>
                <span class="stat-value">{{ currentTask?.total_epochs || 3 }}</span>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon score"><el-icon><Star /></el-icon></div>
              <div class="stat-data">
                <span class="stat-label">模型评分</span>
                <span class="stat-value">92.5</span>
              </div>
            </div>
          </div>

          <!-- Evaluation Content -->
          <div class="evaluation-content">
            <iframe
              v-if="evaluationHtml"
              :srcdoc="evaluationHtml"
              class="evaluation-iframe"
              sandbox="allow-same-origin"
            />

            <div v-else class="evaluation-placeholder">
              <div class="placeholder-content">
                <el-icon :size="64" color="#cbd5e1"><DataAnalysis /></el-icon>
                <h3>评估报告准备中</h3>
                <p>详细的评估指标和可视化图表将在此显示</p>

                <div class="placeholder-features">
                  <div class="feature">
                    <el-icon><TrendCharts /></el-icon>
                    <span>训练曲线</span>
                  </div>
                  <div class="feature">
                    <el-icon><PieChart /></el-icon>
                    <span>指标分布</span>
                  </div>
                  <div class="feature">
                    <el-icon><Document /></el-icon>
                    <span>文本对比</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="empty-result">
          <div class="empty-content">
            <el-icon :size="80" color="#cbd5e1"><Select /></el-icon>
            <h2>选择一个任务查看评估</h2>
            <p>从左侧列表选择一个已完成的训练任务以查看详细评估报告</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTaskStore } from '@/stores/task'
import { ElMessage } from 'element-plus'
import {
  DataLine,
  List,
  Check,
  Close,
  ArrowRight,
  Document,
  Refresh,
  Download,
  TrendCharts,
  Timer,
  CircleCheck,
  Star,
  DataAnalysis,
  PieChart,
  Select
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const taskStore = useTaskStore()

const selectedTaskId = ref('')
const evaluationHtml = ref('')
const loading = ref(false)

const completedTasks = computed(() =>
  taskStore.completedTasks
)

const currentTask = computed(() =>
  taskStore.tasks.find(t => t.id === selectedTaskId.value)
)

onMounted(async () => {
  await taskStore.fetchTasks()
})

function selectTask(task) {
  selectedTaskId.value = task.id
  loadEvaluation()
}

async function loadEvaluation() {
  if (!selectedTaskId.value) return

  loading.value = true
  try {
    const html = await taskStore.fetchEvaluation(selectedTaskId.value)
    evaluationHtml.value = html
  } catch (error) {
    ElMessage.error('加载评估报告失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

function getStatusClass(status) {
  return status === 'COMPLETED' ? 'success' : 'error'
}

function formatTime(time) {
  if (!time) return '-'
  return dayjs(time).format('MM-DD HH:mm')
}

function formatDate(time) {
  if (!time) return '-'
  return dayjs(time).format('YYYY-MM-DD HH:mm')
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  const mins = Math.floor(seconds / 60)
  const hrs = Math.floor(mins / 60)
  if (hrs > 0) {
    return `${hrs}h ${mins % 60}m`
  }
  return `${mins}m`
}
</script>

<style scoped>
.evaluation-page {
  padding-bottom: 40px;
}

/* Header */
.page-header {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 24px 28px;
  margin-bottom: 24px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 16px;
}

.title-icon {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 0 20px rgba(139, 92, 246, 0.3);
}

.title-text h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.title-text p {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 4px 0 0;
}

/* Layout */
.evaluation-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 24px;
}

/* Selector Panel */
.selector-panel {
  position: sticky;
  top: 24px;
  height: fit-content;
}

.panel-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  font-weight: 600;
  color: var(--text-primary);
}

.task-list {
  max-height: calc(100vh - 280px);
  overflow-y: auto;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.task-item:hover {
  background: var(--bg-secondary);
}

.task-item.active {
  background: rgba(102, 126, 234, 0.08);
  border-left: 3px solid var(--primary-color);
}

.task-status-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.task-status-icon.success {
  background: rgba(16, 185, 129, 0.1);
  color: var(--success-color);
}

.task-status-icon.error {
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger-color);
}

.task-info {
  flex: 1;
  min-width: 0;
}

.task-name {
  display: block;
  font-weight: 600;
  color: var(--text-primary);
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-meta {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.selected-icon {
  color: var(--primary-color);
}

.empty-tasks {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
  text-align: center;
}

.empty-tasks p {
  color: var(--text-secondary);
  margin: 12px 0;
}

/* Result Panel */
.result-panel {
  min-height: 600px;
}

.result-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
  overflow: hidden;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px;
  border-bottom: 1px solid var(--border-color);
}

.header-left h2 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.task-tags {
  display: flex;
  gap: 8px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* Stats Row */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  padding: 20px 24px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.stat-icon {
  width: 44px;
  height: 44px;
  background: rgba(102, 126, 234, 0.1);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
  font-size: 20px;
}

.stat-icon.time {
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning-color);
}

.stat-icon.epochs {
  background: rgba(16, 185, 129, 0.1);
  color: var(--success-color);
}

.stat-icon.score {
  background: rgba(139, 92, 246, 0.1);
  color: #8b5cf6;
}

.stat-data {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 12px;
  color: var(--text-muted);
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin-top: 2px;
}

/* Evaluation Content */
.evaluation-content {
  padding: 24px;
  min-height: 400px;
}

.evaluation-iframe {
  width: 100%;
  height: 600px;
  border: none;
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
}

.evaluation-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 2px dashed var(--border-color);
}

.placeholder-content {
  text-align: center;
}

.placeholder-content h3 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 20px 0 8px;
}

.placeholder-content p {
  color: var(--text-secondary);
  margin: 0 0 32px;
}

.placeholder-features {
  display: flex;
  justify-content: center;
  gap: 32px;
}

.feature {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 13px;
}

.feature .el-icon {
  width: 48px;
  height: 48px;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

/* Empty Result */
.empty-result {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 600px;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
}

.empty-content {
  text-align: center;
  padding: 40px;
}

.empty-content h2 {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 20px 0 8px;
}

.empty-content p {
  color: var(--text-secondary);
  margin: 0;
}

/* Responsive */
@media (max-width: 1200px) {
  .evaluation-layout {
    grid-template-columns: 280px 1fr;
  }

  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 992px) {
  .evaluation-layout {
    grid-template-columns: 1fr;
  }

  .selector-panel {
    position: static;
  }

  .task-list {
    max-height: 300px;
  }
}

@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: 1fr;
  }
}
</style>
