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
                <el-icon v-else><Close /></el-icon>
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
        <div v-if="selectedTaskId" v-loading="loading">
          <EvaluationReport
            v-if="evaluationData"
            :data="evaluationData"
            @refresh="loadEvaluation"
            @commentSubmitted="handleCommentSubmitted"
            @reEvaluate="handleReEvaluate"
          />
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
import EvaluationReport from '@/components/Evaluation/EvaluationReport.vue'
import {
  DataLine,
  List,
  Check,
  Close,
  ArrowRight,
  Document,
  Select
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const taskStore = useTaskStore()

const selectedTaskId = ref('')
const evaluationData = ref(null)
const loading = ref(false)

// Include COMPLETED and EVALUATING tasks
const completedTasks = computed(() =>
  taskStore.tasks.filter(t => t.status === 'COMPLETED' || t.status === 'EVALUATING')
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
  evaluationData.value = null
  try {
    const response = await taskStore.fetchEvaluation(selectedTaskId.value)
    if (response.message === 'evaluating') {
      ElMessage.info('模型评估中，请稍候...')
      evaluationData.value = null
    } else if (response.data) {
      evaluationData.value = response.data
    }
  } catch (error) {
    ElMessage.error('加载评估报告失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

function getStatusClass(status) {
  if (status === 'COMPLETED') return 'success'
  if (status === 'EVALUATING') return 'warning'
  return 'error'
}

function formatTime(time) {
  if (!time) return '-'
  return dayjs(time).format('MM-DD HH:mm')
}

function handleCommentSubmitted({ taskId, comment }) {
  // Update local data with the new comment
  if (evaluationData.value && evaluationData.value.task_id === taskId) {
    evaluationData.value.comment = comment
  }
}

function handleReEvaluate({ taskId }) {
  // Update local task status to EVALUATING so UI reflects the change
  const task = taskStore.tasks.find(t => t.id === taskId)
  if (task) {
    task.status = 'EVALUATING'
  }
  if (taskStore.currentTask?.id === taskId) {
    taskStore.currentTask.status = 'EVALUATING'
  }
  evaluationData.value = null
  loadEvaluation()
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

.task-status-icon.warning {
  background: rgba(139, 92, 246, 0.1);
  color: #8b5cf6;
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
</style>
