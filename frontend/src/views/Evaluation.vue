<template>
  <div class="page-container">
    <div class="page-header">
      <h1>生成结果可视化</h1>
      <p>查看风格转换效果的评估报告</p>
    </div>

    <div class="evaluation-container">
      <!-- Task Selection -->
      <el-card class="selection-card">
        <template #header>
          <div class="card-header">
            <span>选择训练任务</span>
          </div>
        </template>

        <el-select
          v-model="selectedTaskId"
          placeholder="选择一个已完成的任务"
          style="width: 100%"
          @change="loadEvaluation"
        >
          <el-option
            v-for="task in completedTasks"
            :key="task.id"
            :label="`${task.name || task.id}`"
            :value="task.id"
          >
            <div class="task-option">
              <span>{{ task.name || '未命名' }}</span>
              <el-tag
                :type="task.status === 'COMPLETED' ? 'success' : 'info'"
                size="small"
              >
                {{ task.status }}
              </el-tag>
            </div>
          </el-option>
        </el-select>
      </el-card>

      <!-- Evaluation Result -->
      <el-card v-if="selectedTaskId" class="result-card" v-loading="loading">
        <template #header>
          <div class="card-header">
            <span>评估报告</span>
            <el-button
              type="primary"
              link
              :icon="Refresh"
              @click="loadEvaluation"
            >
              刷新
            </el-button>
          </div>
        </template>

        <iframe
          v-if="evaluationHtml"
          :srcdoc="evaluationHtml"
          class="evaluation-iframe"
          sandbox="allow-same-origin"
        ></iframe>

        <el-empty v-else description="暂无评估数据" />
      </el-card>

      <el-empty v-else description="请先选择一个训练任务">
        <el-button type="primary" @click="$router.push('/style-training')">
          去训练模型
        </el-button>
      </el-empty>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTaskStore } from '@/stores/task'
import { Refresh } from '@element-plus/icons-vue'

const taskStore = useTaskStore()

const selectedTaskId = ref('')
const evaluationHtml = ref('')
const loading = ref(false)

const completedTasks = computed(() =>
  taskStore.completedTasks
)

onMounted(async () => {
  await taskStore.fetchTasks()
})

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
</script>

<style scoped>
.page-container {
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 8px;
}

.page-header p {
  color: #666;
}

.evaluation-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.selection-card {
  max-width: 600px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.result-card {
  min-height: 500px;
}

.evaluation-iframe {
  width: 100%;
  height: 600px;
  border: none;
  border-radius: 4px;
}
</style>
