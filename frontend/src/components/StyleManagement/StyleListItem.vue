<template>
  <div
    class="list-row"
    :class="statusClass"
    :style="{ animationDelay: `${animationDelay}s` }"
  >
    <div class="list-info" @click="$emit('click', style)">
      <div class="list-icon" :class="taskStatusClass">
        <el-icon><Collection /></el-icon>
      </div>
      <div class="list-text">
        <span class="list-name">{{ style.name }}</span>
        <span class="list-target">
          {{ style.target_style }}
          <el-tag v-if="style.source === 'explored'" size="small" type="warning" class="source-tag">
            <el-icon><Compass /></el-icon> 探索
          </el-tag>
        </span>
      </div>
    </div>

    <div class="list-status" :class="taskStatusClass">
      <span class="status-indicator"></span>
      <span>{{ statusLabel }}</span>
    </div>

    <div class="list-date">
      {{ formattedTime }}
    </div>

    <div class="list-actions">
      <!-- Show progress button when training or evaluating -->
      <el-button
        v-if="isProcessing"
        link
        type="warning"
        :icon="VideoPlay"
        @click="$emit('viewProgress', style)"
      >
        查看进度
      </el-button>
      <el-button
        link
        type="primary"
        :icon="Edit"
        :disabled="isProcessing"
        @click="$emit('edit', style)"
      >
        编辑
      </el-button>
      <el-button
        link
        type="danger"
        :icon="Delete"
        :disabled="isProcessing"
        @click="$emit('delete', style)"
      >
        删除
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  Collection,
  Edit,
  Delete,
  VideoPlay,
  Compass
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const props = defineProps({
  style: {
    type: Object,
    required: true
  },
  animationDelay: {
    type: Number,
    default: 0
  }
})

defineEmits(['click', 'edit', 'delete', 'viewProgress'])

// Use task_status (from Task model) instead of style.status
const taskStatus = computed(() => props.style.task_status || 'PENDING')

// Map task status to CSS class (lowercase for CSS)
const taskStatusClass = computed(() => {
  const statusMap = {
    'PENDING': 'pending',
    'PREPROCESSING': 'preprocessing',
    'PROCESSING': 'training',
    'COMPLETED': 'completed',
    'FAILED': 'failed',
    'EVALUATING': 'evaluating'
  }
  return statusMap[taskStatus.value] || 'pending'
})

// For row-level status class
const statusClass = computed(() => {
  return `status-${taskStatusClass.value}`
})

const statusLabel = computed(() => {
  const labels = {
    'PENDING': '等待中',
    'PREPROCESSING': '数据处理中',
    'PROCESSING': '训练中',
    'COMPLETED': '已完成',
    'FAILED': '失败',
    'EVALUATING': '评估中'
  }
  console.log(taskStatus.value)
  return labels[taskStatus.value] || taskStatus.value
})

const isProcessing = computed(() =>
  taskStatus.value === 'PROCESSING' || taskStatus.value === 'EVALUATING' || taskStatus.value === 'PREPROCESSING'
)

const formattedTime = computed(() => {
  return dayjs(props.style.created_at).format('YYYY-MM-DD HH:mm')
})
</script>

<style scoped>
.list-row {
  display: grid;
  grid-template-columns: 1.5fr 85px 120px 210px;
  gap: 16px;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  transition: all 0.2s ease;
  animation: slideIn 0.3s ease forwards;
  opacity: 0;
  transform: translateX(-10px);
}

@keyframes slideIn {
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.list-row:last-child {
  border-bottom: none;
}

.list-row:hover {
  background: rgba(102, 126, 234, 0.03);
}

.list-info {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.list-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 18px;
  flex-shrink: 0;
}

.list-icon.completed {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.list-icon.training {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.list-icon.pending {
  background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%);
}

.list-icon.preprocessing {
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
}

.list-icon.evaluating {
  background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);
}

.list-icon.failed {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
}

.list-text {
  min-width: 0;
}

.list-name {
  display: block;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.list-target {
  font-size: 12px;
  color: #667eea;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}

.source-tag {
  margin-left: 4px;
}

.list-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
}

.list-status.completed {
  color: #059669;
}

.list-status.training {
  color: #d97706;
}

.list-status.pending {
  color: #64748b;
}

.list-status.preprocessing {
  color: #0891b2;
}

.list-status.preprocessing .status-indicator {
  background: #06b6d4;
  box-shadow: 0 0 6px #06b6d4;
}

.list-status.evaluating {
  color: #7c3aed;
}

.list-status.evaluating .status-indicator {
  background: #8b5cf6;
  box-shadow: 0 0 6px #8b5cf6;
}

.list-status.failed {
  color: #dc2626;
}

.list-status.failed .status-indicator {
  background: #ef4444;
  box-shadow: 0 0 6px #ef4444;
}

.list-status .status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.list-status.completed .status-indicator {
  background: #10b981;
  box-shadow: 0 0 6px #10b981;
}

.list-status.training .status-indicator {
  background: #f59e0b;
  box-shadow: 0 0 6px #f59e0b;
}

.list-date {
  font-size: 13px;
  color: var(--text-muted);
}

.list-actions {
  display: flex;
  gap: 4px;
  justify-content: flex-end;
  align-items: center;
  min-width: 0;
}

.list-actions :deep(.el-button) {
  padding: 4px 8px;
  font-size: 13px;
}

.list-actions :deep(.el-button > span) {
  display: flex;
  align-items: center;
  gap: 2px;
}

@media (max-width: 768px) {
  .list-row {
    grid-template-columns: 1fr 210px;
  }

  .list-status,
  .list-date {
    display: none;
  }
}
</style>
