<template>
  <div
    class="list-row"
    :class="statusClass"
    :style="{ animationDelay: `${animationDelay}s` }"
  >
    <div class="list-info" @click="$emit('click', style)">
      <div class="list-icon" :class="style.status">
        <el-icon><Collection /></el-icon>
      </div>
      <div class="list-text">
        <span class="list-name">{{ style.name }}</span>
        <span class="list-target">{{ style.target_style }}</span>
      </div>
    </div>

    <div class="list-status" :class="style.status">
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
  VideoPlay
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

const statusClass = computed(() => {
  const classes = {
    'pending': 'status-pending',
    'training': 'status-training',
    'completed': 'status-completed',
    'failed': 'status-failed',
    'available': 'status-available',
    'evaluating': 'status-evaluating',
    'preprocessing': 'status-preprocessing'
  }
  return classes[props.style.status] || 'status-pending'
})

const statusLabel = computed(() => {
  const labels = {
    'pending': '待训练',
    'training': '训练中',
    'completed': '已完成',
    'failed': '失败',
    'available': '可用',
    'evaluating': '评估中',
    'preprocessing': '处理训练数据'
  }
  return labels[props.style.status] || props.style.status
})

const isProcessing = computed(() =>
  props.style.status === 'training' || props.style.status === 'evaluating' || props.style.status === 'preprocessing'
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

.list-icon.available {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.list-icon.training {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.list-icon.pending {
  background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%);
}

.list-icon.evaluating {
  background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);
}

.list-icon.preprocessing {
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
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
}

.list-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
}

.list-status.available {
  color: #059669;
}

.list-status.training {
  color: #d97706;
}

.list-status.pending {
  color: #64748b;
}

.list-status.evaluating {
  color: #7c3aed;
}

.list-status.evaluating .status-indicator {
  background: #8b5cf6;
  box-shadow: 0 0 6px #8b5cf6;
}

.list-status.preprocessing {
  color: #0891b2;
}

.list-status.preprocessing .status-indicator {
  background: #06b6d4;
  box-shadow: 0 0 6px #06b6d4;
}

.list-status .status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.list-status.available .status-indicator {
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
