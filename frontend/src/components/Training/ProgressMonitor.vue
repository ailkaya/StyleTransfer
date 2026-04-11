<template>
  <el-dialog
    v-model="visible"
    title="训练进度"
    width="600px"
    :close-on-click-modal="false"
    :show-close="task.status === 'COMPLETED' || task.status === 'FAILED'"
    @close="$emit('close')"
  >
    <div class="progress-content">
      <!-- Status Header -->
      <div class="status-header">
        <el-tag :type="statusType" size="large">{{ statusLabel }}</el-tag>
        <span class="progress-text">{{ task.progress }}%</span>
      </div>

      <!-- Progress Bar -->
      <el-progress
        :percentage="task.progress"
        :status="progressStatus"
        :stroke-width="12"
        striped
        :striped-flow="task.status === 'PROCESSING'"
      />

      <!-- Stats Grid -->
      <div class="stats-grid">
        <div class="stat-item">
          <div class="stat-label">当前轮数</div>
          <div class="stat-value">{{ task.current_epoch || 0 }} / {{ task.total_epochs || 3 }}</div>
        </div>

        <div class="stat-item">
          <div class="stat-label">当前Loss</div>
          <div class="stat-value">{{ task.current_loss ? task.current_loss.toFixed(4) : '-' }}</div>
        </div>

        <div class="stat-item">
          <div class="stat-label">已用时间</div>
          <div class="stat-value">{{ formatDuration(task.elapsed_time) }}</div>
        </div>

        <div class="stat-item">
          <div class="stat-label">预计剩余</div>
          <div class="stat-value">{{ formatDuration(task.estimated_remaining) }}</div>
        </div>
      </div>

      <!-- Log Viewer -->
      <div class="log-section">
        <div class="log-header">
          <span>训练日志</span>
          <el-button link :icon="Refresh" @click="refreshLogs">刷新</el-button>
        </div>
        <div ref="logContainer" class="log-content">
          <div
            v-for="(line, index) in logLines"
            :key="index"
            class="log-line"
          >
            {{ line }}
          </div>
          <div v-if="logLines.length === 0" class="log-empty">暂无日志</div>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button
        v-if="task.status === 'COMPLETED'"
        type="primary"
        @click="goToEvaluation"
      >
        查看评估
      </el-button>
      <el-button @click="$emit('close')">
        {{ task.status === 'PROCESSING' ? '后台运行' : '关闭' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'

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
const logLines = ref([])

const statusType = computed(() => {
  const types = {
    'PENDING': 'info',
    'PROCESSING': 'warning',
    'COMPLETED': 'success',
    'FAILED': 'danger'
  }
  return types[props.task.status] || 'info'
})

const statusLabel = computed(() => {
  const labels = {
    'PENDING': '等待中',
    'PROCESSING': '训练中',
    'COMPLETED': '已完成',
    'FAILED': '失败'
  }
  return labels[props.task.status] || props.task.status
})

const progressStatus = computed(() => {
  if (props.task.status === 'COMPLETED') return 'success'
  if (props.task.status === 'FAILED') return 'exception'
  return null
})

// Parse logs from task
watch(() => props.task.logs, (logs) => {
  if (logs) {
    logLines.value = logs.split('\n').filter(line => line.trim())
    nextTick(() => {
      if (logContainer.value) {
        logContainer.value.scrollTop = logContainer.value.scrollHeight
      }
    })
  }
}, { immediate: true })

function formatDuration(seconds) {
  if (!seconds) return '-'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (mins > 0) {
    return `${mins}分${secs}秒`
  }
  return `${secs}秒`
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
.progress-content {
  padding: 0 10px;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.progress-text {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a2e;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin: 24px 0;
}

.stat-item {
  background: #f5f7fa;
  padding: 12px 16px;
  border-radius: 8px;
}

.stat-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.log-section {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  font-size: 14px;
  font-weight: 500;
}

.log-content {
  height: 200px;
  overflow-y: auto;
  padding: 12px;
  background: #1a1a2e;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.log-line {
  color: #a0aec0;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-empty {
  color: #666;
  text-align: center;
  padding: 40px;
}
</style>
