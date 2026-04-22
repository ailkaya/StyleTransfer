<template>
  <div class="system-monitoring-page">
    <!-- Header -->
    <div class="monitoring-bar">
      <div class="bar-left">
        <el-icon :size="18"><Monitor /></el-icon>
        <span class="bar-label">系统监控</span>
        <el-tag size="small" type="info" effect="light">实时</el-tag>
      </div>
      <div class="bar-right">
        <el-tag :type="connectionStatus.type" size="small" effect="light">
          <el-icon v-if="connectionStatus.icon" :size="12" class="status-icon">
            <component :is="connectionStatus.icon" />
          </el-icon>
          {{ connectionStatus.text }}
        </el-tag>
      </div>
    </div>

    <!-- Metrics Grid -->
    <div class="monitoring-content">
      <div class="metrics-grid">
        <!-- CPU Card -->
        <div class="metric-card">
          <div class="metric-header">
            <div class="metric-icon cpu-icon">
              <el-icon :size="20"><Cpu /></el-icon>
            </div>
            <div class="metric-title">
              <h3>CPU</h3>
              <p v-if="stats.cpu.available">
                {{ stats.cpu.count.logical }} 逻辑核心 / {{ stats.cpu.count.physical }} 物理核心
              </p>
              <p v-else>不可用</p>
            </div>
          </div>
          <div v-if="stats.cpu.available" class="metric-body">
            <div class="percent-value" :style="{ color: getPercentColor(stats.cpu.percent) }">
              {{ stats.cpu.percent.toFixed(1) }}%
            </div>
            <el-progress
              :percentage="Math.min(stats.cpu.percent, 100)"
              :color="progressColors"
              :stroke-width="12"
              :show-text="false"
            />
          </div>
          <div v-else class="metric-unavailable">
            <el-icon :size="32"><Warning /></el-icon>
            <span>psutil 未安装</span>
          </div>
        </div>

        <!-- Memory Card -->
        <div class="metric-card">
          <div class="metric-header">
            <div class="metric-icon memory-icon">
              <el-icon :size="20"><Collection /></el-icon>
            </div>
            <div class="metric-title">
              <h3>内存</h3>
              <p v-if="stats.memory.available">
                {{ stats.memory.used_gb }} GB / {{ stats.memory.total_gb }} GB
              </p>
              <p v-else>不可用</p>
            </div>
          </div>
          <div v-if="stats.memory.available" class="metric-body">
            <div class="percent-value" :style="{ color: getPercentColor(stats.memory.percent) }">
              {{ stats.memory.percent.toFixed(1) }}%
            </div>
            <el-progress
              :percentage="Math.min(stats.memory.percent, 100)"
              :color="progressColors"
              :stroke-width="12"
              :show-text="false"
            />
          </div>
          <div v-else class="metric-unavailable">
            <el-icon :size="32"><Warning /></el-icon>
            <span>psutil 未安装</span>
          </div>
        </div>
      </div>

      <!-- GPU Section -->
      <div class="gpu-section">
        <div class="section-header">
          <div class="section-icon">
            <el-icon :size="18"><Gpu /></el-icon>
          </div>
          <h3>GPU</h3>
          <el-tag v-if="stats.gpu.available" size="small" type="success">{{ stats.gpu.count }} 设备</el-tag>
          <el-tag v-else size="small" type="info">未检测到</el-tag>
        </div>

        <div v-if="stats.gpu.available" class="gpu-grid">
          <div v-for="gpu in stats.gpu.gpus" :key="gpu.id" class="metric-card gpu-card">
            <div class="metric-header">
              <div class="metric-icon gpu-icon">
                <el-icon :size="20"><VideoCamera /></el-icon>
              </div>
              <div class="metric-title">
                <h3>{{ gpu.name }}</h3>
                <p>
                  {{ gpu.allocated_mb.toLocaleString() }} MB / {{ gpu.total_mb.toLocaleString() }} MB
                </p>
              </div>
            </div>
            <div class="metric-body">
              <div class="percent-value" :style="{ color: getPercentColor((gpu.allocated_mb / gpu.total_mb) * 100) }">
                {{ ((gpu.allocated_mb / gpu.total_mb) * 100).toFixed(1) }}%
              </div>
              <el-progress
                :percentage="Math.min((gpu.allocated_mb / gpu.total_mb) * 100, 100)"
                :color="progressColors"
                :stroke-width="12"
                :show-text="false"
              />
              <div class="gpu-details">
                <span>已分配: {{ gpu.allocated_mb.toLocaleString() }} MB</span>
                <span>预留: {{ gpu.reserved_mb.toLocaleString() }} MB</span>
                <span>空闲: {{ gpu.free_mb.toLocaleString() }} MB</span>
                <span v-if="gpu.utilization_percent !== null">利用率: {{ gpu.utilization_percent }}%</span>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="empty-state">
          <div class="empty-card">
            <div class="empty-icon">
              <el-icon :size="64"><VideoCamera /></el-icon>
            </div>
            <h3>未检测到 GPU</h3>
            <p>当前系统没有可用的 CUDA 设备，或 torch 未安装。</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Monitor,
  Cpu,
  Collection,
  Warning,
  VideoCamera,
  CircleCheck,
  CircleClose
} from '@element-plus/icons-vue'
import { monitoringApi } from '@/api/monitoring'

const stats = ref({
  cpu: { available: false },
  memory: { available: false },
  gpu: { available: false, cuda_available: false }
})
const loading = ref(false)
const lastFetchTime = ref(null)

const progressColors = [
  { color: '#10b981', percentage: 60 },
  { color: '#f59e0b', percentage: 85 },
  { color: '#ef4444', percentage: 100 }
]

function getPercentColor(percent) {
  if (percent < 60) return '#10b981'
  if (percent < 85) return '#f59e0b'
  return '#ef4444'
}

const connectionStatus = computed(() => {
  if (!lastFetchTime.value) {
    return { text: '连接中...', type: 'info', icon: null }
  }
  const elapsed = Date.now() - lastFetchTime.value
  if (elapsed < 15000) {
    return { text: '实时更新中', type: 'success', icon: 'CircleCheck' }
  }
  return { text: '更新延迟', type: 'warning', icon: 'CircleClose' }
})

async function fetchStats() {
  loading.value = true
  try {
    const res = await monitoringApi.getStats()
    if (res.code === 200 && res.data) {
      stats.value = res.data
      lastFetchTime.value = Date.now()
    }
  } catch (error) {
    console.error('Failed to fetch system stats:', error)
  } finally {
    loading.value = false
  }
}

let pollInterval = null

function startPolling() {
  fetchStats()
  pollInterval = setInterval(() => {
    fetchStats()
  }, 10000)
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

onMounted(() => {
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<script>
// Local component registration for icons used dynamically
export default {
  components: {
    Gpu: VideoCamera
  }
}
</script>

<style scoped>
.system-monitoring-page {
  height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
}

.monitoring-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  margin-bottom: 12px;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
}

.bar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-primary);
}

.bar-label {
  font-size: 15px;
  font-weight: 600;
}

.bar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-icon {
  margin-right: 4px;
  vertical-align: middle;
}

.monitoring-content {
  flex: 1;
  overflow-y: auto;
  padding: 0 4px;
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.metric-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.metric-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.metric-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.cpu-icon {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.memory-icon {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.gpu-icon {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.metric-title h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px;
}

.metric-title p {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0;
}

.metric-body .percent-value {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
}

.metric-unavailable {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px;
  color: var(--text-muted);
}

/* GPU Section */
.gpu-section {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.section-header h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.section-icon {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.gpu-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.gpu-card {
  padding: 16px;
}

.gpu-details {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  margin-top: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.gpu-details span {
  background: var(--bg-secondary);
  padding: 4px 10px;
  border-radius: 6px;
}

/* Empty State */
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
}

.empty-card {
  text-align: center;
  padding: 32px;
  max-width: 320px;
}

.empty-icon {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, rgba(79, 172, 254, 0.1) 0%, rgba(0, 242, 254, 0.1) 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  color: #4facfe;
}

.empty-card h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.empty-card p {
  color: var(--text-secondary);
  margin: 0;
  font-size: 13px;
}

/* Responsive */
@media (max-width: 768px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .gpu-grid {
    grid-template-columns: 1fr;
  }
}
</style>
