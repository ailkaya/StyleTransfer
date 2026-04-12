<template>
  <el-dialog
    v-model="visible"
    title=""
    width="560px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    class="progress-dialog"
    destroy-on-close
    @closed="stopPolling"
  >
    <!-- Header -->
    <div class="dialog-header-bar">
      <div class="dialog-icon" :class="statusClass">
        <el-icon :size="22"><Loading v-if="isProcessing" /><Monitor v-else /></el-icon>
      </div>
      <div class="dialog-title-wrapper">
        <span class="dialog-title">训练进度</span>
        <span class="dialog-subtitle">{{ styleName }}</span>
      </div>
      <div class="status-badge" :class="statusClass">
        {{ statusText }}
      </div>
    </div>

    <!-- Body -->
    <div class="dialog-body">
      <!-- Error Message -->
      <div v-if="task?.error_message" class="error-alert">
        <el-icon><Warning /></el-icon>
        <span>{{ task.error_message }}</span>
      </div>

      <!-- Progress Overview -->
      <div class="progress-overview">
        <div class="progress-circle-wrapper">
          <el-progress
            type="dashboard"
            :percentage="progressPercentage"
            :color="progressColors"
            :stroke-width="10"
            :width="140"
          />
          <div class="progress-label">总体进度</div>
        </div>

        <div class="progress-stats">
          <div class="stat-item">
            <div class="stat-label">
              <el-icon><Timer /></el-icon>
              已用时间
            </div>
            <div class="stat-value">{{ formatDuration(task?.elapsed_time) }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">
              <el-icon><Clock /></el-icon>
              预计剩余
            </div>
            <div class="stat-value">{{ formatDuration(task?.estimated_remaining) }}</div>
          </div>
          <div class="stat-item" v-if="task?.current_loss != null">
            <div class="stat-label">
              <el-icon><TrendCharts /></el-icon>
              当前 Loss
            </div>
            <div class="stat-value loss">{{ formatLoss(task?.current_loss) }}</div>
          </div>
        </div>
      </div>

      <!-- Epoch Progress -->
      <div class="epoch-section">
        <div class="section-header">
          <span class="section-title">
            <el-icon><DataLine /></el-icon>
            Epoch 进度
          </span>
          <span class="epoch-text">{{ currentEpoch }} / {{ totalEpochs }}</span>
        </div>
        <el-progress
          :percentage="epochPercentage"
          :stroke-width="8"
          :color="progressColors"
          :show-text="false"
        />
      </div>

      <!-- Evaluation Progress (only show when evaluating) -->
      <div v-if="isEvaluating" class="evaluation-section">
        <div class="section-header">
          <span class="section-title">
            <el-icon><DocumentChecked /></el-icon>
            评估进度
          </span>
          <span class="eval-status">正在进行模型评估...</span>
        </div>
        <div class="eval-progress-bar">
          <div class="eval-progress-fill" :style="{ width: `${evalProgress}%` }"></div>
        </div>
        <div class="eval-steps">
          <div
            v-for="(step, idx) in evalSteps"
            :key="idx"
            class="eval-step"
            :class="{ active: idx <= currentEvalStep, completed: idx < currentEvalStep }"
          >
            <div class="step-dot">
              <el-icon v-if="idx < currentEvalStep"><Check /></el-icon>
              <span v-else>{{ idx + 1 }}</span>
            </div>
            <span class="step-label">{{ step }}</span>
          </div>
        </div>
      </div>

      <!-- Live Indicator -->
      <div class="live-indicator" :class="{ polling: isPolling }">
        <span class="live-dot"></span>
        <span>{{ isPolling ? '实时更新中' : '已暂停' }}</span>
        <span class="last-update">最后更新: {{ lastUpdateTime }}</span>
      </div>
    </div>

    <!-- Footer -->
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">
          {{ isProcessing ? '后台运行' : '关闭' }}
        </el-button>
        <el-button
          v-if="isProcessing"
          type="primary"
          :loading="refreshing"
          @click="refreshNow"
        >
          <el-icon><Refresh /></el-icon>
          立即刷新
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import {
  Loading,
  Monitor,
  Timer,
  Clock,
  TrendCharts,
  DataLine,
  DocumentChecked,
  Refresh,
  Check,
  Warning
} from '@element-plus/icons-vue'
import { taskApi } from '@/api/tasks'
import { ElMessage } from 'element-plus'

const props = defineProps({
  styleId: {
    type: String,
    default: ''
  },
  styleName: {
    type: String,
    default: ''
  },
  styleStatus: {
    type: String,
    default: ''
  }
})

const visible = defineModel('visible', { default: false })

const task = ref(null)
const isPolling = ref(false)
const refreshing = ref(false)
const lastUpdateTime = ref('--:--:--')
const pollInterval = ref(null)
const currentEvalStep = ref(0)

const POLLING_INTERVAL = 3000 // 3 seconds

const evalSteps = ['准备数据', '生成样本', '计算指标', '生成报告']

const progressColors = [
  { color: '#f56c6c', percentage: 20 },
  { color: '#e6a23c', percentage: 40 },
  { color: '#5cb87a', percentage: 60 },
  { color: '#1989fa', percentage: 80 },
  { color: '#6f7ad3', percentage: 100 }
]

const isProcessing = computed(() => {
  return task.value?.status === 'PENDING' || task.value?.status === 'PROCESSING'
})

const isEvaluating = computed(() => {
  return props.styleStatus === 'evaluating' || task.value?.status === 'EVALUATING'
})

const statusClass = computed(() => {
  const status = task.value?.status || props.styleStatus
  const classes = {
    'PENDING': 'status-pending',
    'PROCESSING': 'status-training',
    'COMPLETED': 'status-completed',
    'FAILED': 'status-failed',
    'EVALUATING': 'status-evaluating',
    'training': 'status-training',
    'evaluating': 'status-evaluating',
    'available': 'status-completed',
    'failed': 'status-failed'
  }
  return classes[status] || 'status-pending'
})

const statusText = computed(() => {
  const status = task.value?.status || props.styleStatus
  const texts = {
    'PENDING': '等待中',
    'PROCESSING': '训练中',
    'COMPLETED': '已完成',
    'FAILED': '失败',
    'EVALUATING': '评估中',
    'training': '训练中',
    'evaluating': '评估中',
    'available': '可用',
    'failed': '失败'
  }
  return texts[status] || status
})

const progressPercentage = computed(() => {
  return task.value?.progress || 0
})

// Fix: Use computed properties with proper fallback
const currentEpoch = computed(() => {
  return task.value?.current_epoch ?? 0
})

const totalEpochs = computed(() => {
  return task.value?.total_epochs ?? 0
})

const epochPercentage = computed(() => {
  const total = totalEpochs.value
  const current = currentEpoch.value
  if (!total || total <= 0) return 0
  return Math.round((current / total) * 100)
})

const evalProgress = computed(() => {
  return ((currentEvalStep.value + 1) / evalSteps.length) * 100
})

// Fix: Handle null/undefined properly
function formatDuration(seconds) {
  if (seconds == null || seconds === undefined || seconds < 0) return '--'
  const numSeconds = Number(seconds)
  if (isNaN(numSeconds)) return '--'

  const hours = Math.floor(numSeconds / 3600)
  const mins = Math.floor((numSeconds % 3600) / 60)
  const secs = Math.floor(numSeconds % 60)

  if (hours > 0) {
    return `${hours}h ${mins}m ${secs}s`
  }
  if (mins > 0) {
    return `${mins}m ${secs}s`
  }
  return `${secs}s`
}

function formatLoss(loss) {
  if (loss == null || loss === undefined) return '--'
  if (typeof loss === 'number') {
    return loss.toFixed(4)
  }
  // Handle JSON object loss
  try {
    const lossObj = typeof loss === 'string' ? JSON.parse(loss) : loss
    if (lossObj && typeof lossObj === 'object') {
      const values = Object.values(lossObj).filter(v => typeof v === 'number')
      if (values.length > 0) {
        return values[0].toFixed(4)
      }
    }
  } catch (e) {
    // ignore
  }
  return String(loss).substring(0, 10)
}

async function fetchTaskData() {
  if (!props.styleId) return

  try {
    // Step 1: Get the task list to find the task ID
    const listResponse = await taskApi.getByStyleId(props.styleId)
    const tasks = listResponse.data?.items || []

    if (tasks.length === 0) {
      console.warn('No task found for style:', props.styleId)
      return
    }

    const taskId = tasks[0].id

    // Step 2: Get full task details (includes epoch, time, loss data)
    const detailResponse = await taskApi.getFullTask(taskId)
    const fullTask = detailResponse.data

    if (fullTask) {
      task.value = fullTask
      lastUpdateTime.value = new Date().toLocaleTimeString()

      // Update evaluation step simulation
      if (isEvaluating.value) {
        updateEvalStep()
      }

      // Auto-stop polling if task is completed or failed
      if (fullTask.status === 'COMPLETED' || fullTask.status === 'FAILED') {
        stopPolling()
      }
    }
  } catch (error) {
    console.error('Failed to fetch task:', error)
  }
}

function updateEvalStep() {
  // Simulate evaluation steps based on progress
  const progress = task.value?.progress || 0
  if (progress >= 90) {
    currentEvalStep.value = 3
  } else if (progress >= 75) {
    currentEvalStep.value = 2
  } else if (progress >= 60) {
    currentEvalStep.value = 1
  } else {
    currentEvalStep.value = 0
  }
}

function startPolling() {
  if (pollInterval.value) return
  isPolling.value = true

  // Fetch immediately
  fetchTaskData()

  // Then poll every N seconds
  pollInterval.value = setInterval(() => {
    fetchTaskData()
  }, POLLING_INTERVAL)
}

function stopPolling() {
  isPolling.value = false
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
    pollInterval.value = null
  }
}

async function refreshNow() {
  refreshing.value = true
  await fetchTaskData()
  ElMessage.success('已刷新')
  refreshing.value = false
}

// Watch visibility to start/stop polling
watch(visible, (val) => {
  if (val) {
    startPolling()
  } else {
    stopPolling()
  }
})

// Expose for parent
defineExpose({
  refreshNow
})
</script>

<style scoped>
.dialog-header-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  margin: -20px -20px 0;
  border-radius: 6px;
}

.dialog-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.8; }
}

.dialog-icon.status-pending {
  background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%);
}

.dialog-icon.status-training {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.dialog-icon.status-completed {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  animation: none;
}

.dialog-icon.status-failed {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  animation: none;
}

.dialog-icon.status-evaluating {
  background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);
}

.dialog-title-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.dialog-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
}

.dialog-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.status-badge {
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  color: white;
}

.status-badge.status-pending {
  background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%);
}

.status-badge.status-training {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.status-badge.status-completed {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.status-badge.status-failed {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
}

.status-badge.status-evaluating {
  background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);
}

.dialog-body {
  padding: 20px 0;
}

.error-alert {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 10px;
  margin-bottom: 20px;
  color: #dc2626;
  font-size: 13px;
}

.progress-overview {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 24px;
}

.progress-circle-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.progress-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.progress-stats {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-radius: 10px;
}

.stat-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-value.loss {
  color: #667eea;
  font-family: monospace;
}

.epoch-section,
.evaluation-section {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.epoch-text,
.eval-status {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

/* Evaluation Progress */
.eval-progress-bar {
  height: 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 16px;
}

.eval-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #8b5cf6 0%, #6d28d9 100%);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.eval-steps {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.eval-step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  opacity: 0.4;
  transition: all 0.3s ease;
}

.eval-step.active {
  opacity: 1;
}

.eval-step.completed {
  opacity: 0.7;
}

.eval-step.completed .step-dot {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.step-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 12px;
  font-weight: 600;
  transition: all 0.3s ease;
}

.step-label {
  font-size: 12px;
  color: var(--text-secondary);
  text-align: center;
}

/* Live Indicator */
.live-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border-radius: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

.live-indicator.polling .live-dot {
  animation: blink 1.5s infinite;
  background: #10b981;
}

.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
}

@keyframes blink {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
}

.last-update {
  margin-left: auto;
  font-family: monospace;
}

/* Footer */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.dialog-footer .el-button--primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

/* Responsive */
@media (max-width: 600px) {
  .progress-overview {
    flex-direction: column;
    gap: 16px;
  }

  .progress-stats {
    width: 100%;
  }

  .eval-steps {
    flex-wrap: wrap;
  }

  .step-label {
    display: none;
  }
}
</style>
