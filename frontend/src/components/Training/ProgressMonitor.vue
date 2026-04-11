<template>
  <el-dialog
    v-model="visible"
    title="训练进度监控"
    width="700px"
    :close-on-click-modal="false"
    :show-close="task.status === 'COMPLETED' || task.status === 'FAILED'"
    class="progress-dialog"
    @close="$emit('close')"
  >
    <div class="progress-content">
      <!-- Status Banner -->
      <div class="status-banner" :class="statusClass">
        <div class="banner-icon">
          <el-icon :size="24">
            <Clock v-if="task.status === 'PENDING'" />
            <Loading v-else-if="task.status === 'PROCESSING'" class="spin" />
            <CircleCheck v-else-if="task.status === 'COMPLETED'" />
            <CircleClose v-else />
          </el-icon>
        </div>
        <div class="banner-text">
          <h3>{{ statusTitle }}</h3>
          <p>{{ statusDescription }}</p>
        </div>
        <div class="banner-percentage">
          {{ task.progress }}%
        </div>
      </div>

      <!-- Progress Bar -->
      <div class="progress-section">
        <div class="progress-bar-container">
          <div class="progress-bar" :style="{ width: `${task.progress}%` }" :class="statusClass">
            <div class="progress-shine"></div>
          </div>
        </div>
        <div class="progress-labels">
          <span>准备中</span>
          <span>训练中</span>
          <span>完成</span>
        </div>
      </div>

      <!-- Stats Cards -->
      <div class="stats-row">
        <div class="stat-box">
          <div class="stat-icon">
            <el-icon><Tickets /></el-icon>
          </div>
          <div class="stat-content">
            <span class="stat-label">训练轮数</span>
            <span class="stat-value">{{ task.current_epoch || 0 }} / {{ task.total_epochs || 3 }}</span>
          </div>
        </div>

        <div class="stat-box">
          <div class="stat-icon loss">
            <el-icon><TrendCharts /></el-icon>
          </div>
          <div class="stat-content">
            <span class="stat-label">当前 Loss</span>
            <span class="stat-value">{{ task.current_loss ? task.current_loss.toFixed(4) : '-' }}</span>
          </div>
        </div>

        <div class="stat-box">
          <div class="stat-icon time">
            <el-icon><Timer /></el-icon>
          </div>
          <div class="stat-content">
            <span class="stat-label">已用时间</span>
            <span class="stat-value">{{ formatDuration(task.elapsed_time) }}</span>
          </div>
        </div>

        <div class="stat-box">
          <div class="stat-icon remaining">
            <el-icon><AlarmClock /></el-icon>
          </div>
          <div class="stat-content">
            <span class="stat-label">预计剩余</span>
            <span class="stat-value">{{ formatDuration(task.estimated_remaining) }}</span>
          </div>
        </div>
      </div>

      <!-- Loss Chart (placeholder) -->
      <div class="chart-section">
        <div class="section-header">
          <el-icon><DataLine /></el-icon>
          <span>Loss 曲线</span>
        </div>
        <div class="chart-placeholder">
          <div class="chart-mock">
            <div class="chart-line"></div>
            <div class="chart-points">
              <div v-for="i in 6" :key="i" class="point" :style="{ left: `${i * 15}%`, bottom: `${20 + Math.random() * 40}%` }"></div>
            </div>
          </div>
          <div class="chart-labels">
            <span v-for="i in 6" :key="i">Epoch {{ i }}</span>
          </div>
        </div>
      </div>

      <!-- Log Viewer -->
      <div class="log-section">
        <div class="log-header">
          <div class="log-title">
            <el-icon><Document /></el-icon>
            <span>训练日志</span>
          </div>
          <el-button link :icon="Refresh" @click="refreshLogs">
            刷新
          </el-button>
        </div>
        <div ref="logContainer" class="log-content">
          <div
            v-for="(line, index) in logLines"
            :key="index"
            class="log-line"
          >
            <span class="log-time">{{ getLogTime(line) }}</span>
            <span class="log-message">{{ getLogMessage(line) }}</span>
          </div>
          <div v-if="logLines.length === 0" class="log-empty">
            <el-icon :size="32"><Document /></el-icon>
            <p>暂无日志</p>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button
          v-if="task.status === 'COMPLETED'"
          type="primary"
          size="large"
          :icon="View"
          @click="goToEvaluation"
        >
          查看评估
        </el-button>
        <el-button
          size="large"
          @click="$emit('close')"
        >
          {{ task.status === 'PROCESSING' ? '后台运行' : '关闭' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import {
  Refresh,
  View,
  Clock,
  Loading,
  CircleCheck,
  CircleClose,
  Tickets,
  TrendCharts,
  Timer,
  AlarmClock,
  DataLine,
  Document
} from '@element-plus/icons-vue'

const props = defineProps({
  task: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close', 'refresh'])

const router = useRouter()
const visible = ref(true)
const logContainer = ref(null)
const logLines = ref([
  '[INFO] 初始化训练环境...',
  '[INFO] 加载预训练模型...',
  '[INFO] 开始预处理训练数据...',
  '[INFO] 数据分块完成，共 12 个 chunk',
  '[INFO] 开始训练 Epoch 1/3...',
])

const statusClass = computed(() => {
  const classes = {
    'PENDING': 'status-pending',
    'PROCESSING': 'status-processing',
    'COMPLETED': 'status-completed',
    'FAILED': 'status-failed'
  }
  return classes[props.task.status] || 'status-pending'
})

const statusTitle = computed(() => {
  const titles = {
    'PENDING': '等待中',
    'PROCESSING': '训练中',
    'COMPLETED': '训练完成',
    'FAILED': '训练失败'
  }
  return titles[props.task.status] || '未知状态'
})

const statusDescription = computed(() => {
  const descriptions = {
    'PENDING': '任务正在排队等待处理',
    'PROCESSING': `正在训练第 ${props.task.current_epoch || 1} 轮`,
    'COMPLETED': '模型训练成功完成',
    'FAILED': '训练过程中出现错误'
  }
  return descriptions[props.task.status] || ''
})

// Simulate log updates based on progress
watch(() => props.task.progress, (newProgress) => {
  if (newProgress > 0 && newProgress % 20 === 0) {
    const epoch = Math.ceil(newProgress / 33)
    const loss = (0.5 - newProgress / 200 + Math.random() * 0.1).toFixed(4)
    logLines.value.push(`[INFO] Epoch ${epoch}/3 - Loss: ${loss} - Progress: ${newProgress}%`)
    nextTick(() => {
      if (logContainer.value) {
        logContainer.value.scrollTop = logContainer.value.scrollHeight
      }
    })
  }
  if (props.task.status === 'COMPLETED') {
    logLines.value.push('[INFO] 训练完成，保存模型...')
    logLines.value.push('[INFO] 模型已保存至: ./models/adapters/')
  }
}, { immediate: true })

function formatDuration(seconds) {
  if (!seconds) return '-'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (mins > 0) {
    return `${mins}分${secs.toString().padStart(2, '0')}秒`
  }
  return `${secs}秒`
}

function getLogTime(line) {
  const match = line.match(/^\[(\w+)\]/)
  if (match) {
    const now = new Date()
    return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
  }
  return ''
}

function getLogMessage(line) {
  return line.replace(/^\[\w+\]\s*/, '')
}

function refreshLogs() {
  emit('refresh')
}

function goToEvaluation() {
  visible.value = false
  router.push({
    path: '/evaluation',
    query: { taskId: props.task.id }
  })
}
</script>

<style scoped>
/* Dialog Customization */
:deep(.progress-dialog .el-dialog__header) {
  padding: 20px 24px;
  margin-right: 0;
  border-bottom: 1px solid var(--border-color);
}

:deep(.progress-dialog .el-dialog__body) {
  padding: 0;
}

:deep(.progress-dialog .el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
}

.progress-content {
  padding: 24px;
}

/* Status Banner */
.status-banner {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  border-radius: var(--radius-lg);
  margin-bottom: 24px;
  transition: all var(--transition-fast);
}

.status-banner.status-pending {
  background: linear-gradient(135deg, rgba(148, 163, 184, 0.1) 0%, rgba(100, 116, 139, 0.1) 100%);
  border: 1px solid rgba(148, 163, 184, 0.3);
}

.status-banner.status-processing {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(217, 119, 6, 0.1) 100%);
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.status-banner.status-completed {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%);
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.status-banner.status-failed {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(220, 38, 38, 0.1) 100%);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.banner-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.status-pending .banner-icon {
  background: rgba(148, 163, 184, 0.2);
  color: #64748b;
}

.status-processing .banner-icon {
  background: rgba(245, 158, 11, 0.2);
  color: #d97706;
}

.status-completed .banner-icon {
  background: rgba(16, 185, 129, 0.2);
  color: #059669;
}

.status-failed .banner-icon {
  background: rgba(239, 68, 68, 0.2);
  color: #dc2626;
}

.banner-icon .spin {
  animation: spin 2s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.banner-text {
  flex: 1;
}

.banner-text h3 {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 4px;
  color: var(--text-primary);
}

.banner-text p {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

.banner-percentage {
  font-size: 32px;
  font-weight: 800;
  color: var(--text-primary);
}

/* Progress Section */
.progress-section {
  margin-bottom: 24px;
}

.progress-bar-container {
  height: 12px;
  background: var(--bg-secondary);
  border-radius: 6px;
  overflow: hidden;
  position: relative;
}

.progress-bar {
  height: 100%;
  border-radius: 6px;
  transition: width 0.5s ease, background 0.3s ease;
  position: relative;
  overflow: hidden;
}

.progress-bar.status-pending { background: #94a3b8; }
.progress-bar.status-processing { background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%); }
.progress-bar.status-completed { background: linear-gradient(90deg, #10b981 0%, #059669 100%); }
.progress-bar.status-failed { background: #ef4444; }

.progress-shine {
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
  animation: shine 2s infinite;
}

@keyframes shine {
  to { left: 100%; }
}

.progress-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

/* Stats Row */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.stat-icon {
  width: 40px;
  height: 40px;
  background: rgba(102, 126, 234, 0.1);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
  font-size: 20px;
}

.stat-icon.loss {
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning-color);
}

.stat-icon.time {
  background: rgba(16, 185, 129, 0.1);
  color: var(--success-color);
}

.stat-icon.remaining {
  background: rgba(59, 130, 246, 0.1);
  color: var(--info-color);
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 2px;
}

.stat-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

/* Chart Section */
.chart-section {
  margin-bottom: 24px;
  padding: 20px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.chart-placeholder {
  position: relative;
}

.chart-mock {
  height: 120px;
  position: relative;
  background: linear-gradient(180deg, rgba(102, 126, 234, 0.1) 0%, transparent 100%);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.chart-line {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--primary-color);
}

.chart-points {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  top: 0;
}

.point {
  position: absolute;
  width: 8px;
  height: 8px;
  background: var(--primary-color);
  border-radius: 50%;
  border: 2px solid white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.chart-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 11px;
  color: var(--text-muted);
}

/* Log Section */
.log-section {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.log-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.log-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.log-content {
  height: 200px;
  overflow-y: auto;
  padding: 12px 16px;
  background: #0f172a;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.8;
}

.log-line {
  display: flex;
  gap: 12px;
  color: #94a3b8;
}

.log-time {
  color: #64748b;
  flex-shrink: 0;
}

.log-message {
  color: #e2e8f0;
}

.log-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #475569;
  gap: 8px;
}

/* Dialog Footer */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* Responsive */
@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
