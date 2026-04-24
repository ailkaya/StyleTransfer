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

        <div v-if="stats.gpu.available" class="metrics-grid">
          <div
            v-for="gpu in stats.gpu.gpus"
            :key="gpu.id"
            class="metric-card"
          >
            <!-- Header -->
            <div class="metric-header">
              <div class="metric-icon gpu-icon">
                <el-icon :size="20"><VideoCamera /></el-icon>
              </div>
              <div class="metric-title">
                <h3>GPU {{ gpu.id }}</h3>
                <p>{{ gpu.name }}</p>
              </div>
            </div>

            <!-- Body -->
            <div class="metric-body">
              <!-- 利用率 -->
              <div
                class="percent-value"
                :style="{ color: getPercentColor(gpu.utilization_percent ?? 0) }"
              >
                {{ gpu.utilization_percent !== null ? gpu.utilization_percent.toFixed(0) + '%' : '-' }}
              </div>

              <!-- 进度条（显存使用） -->
              <el-progress
                :percentage="Math.min(((gpu.allocated_mb / gpu.total_mb) * 100) || 0, 100)"
                :color="progressColors"
                :stroke-width="12"
                :show-text="false"
              />

              <!-- 显存信息 -->
              <p style="margin-top: 8px; font-size: 12px; color: var(--text-secondary);">
                {{ gpu.allocated_mb.toLocaleString() }} / {{ gpu.total_mb.toLocaleString() }} MB
              </p>
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

      // GPU 数据仅用于实时展示，不保留历史趋势
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
import { VideoCamera } from '@element-plus/icons-vue'

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
  flex-wrap: wrap;
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

  .gpu-current-stats {
    grid-template-columns: 1fr;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
