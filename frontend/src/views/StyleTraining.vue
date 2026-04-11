<template>
  <div class="page-container">
    <div class="page-header">
      <h1>风格迁移模型训练</h1>
      <p>创建自定义风格，上传示例文本进行训练</p>
    </div>

    <div class="training-form">
      <!-- Basic Info -->
      <el-card class="form-section">
        <template #header>
          <div class="section-header">
            <el-icon><InfoFilled /></el-icon>
            <span>基本信息</span>
          </div>
        </template>

        <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
          <el-form-item label="风格名称" prop="name">
            <el-input v-model="form.name" placeholder="例如：幽默风格" maxlength="50" show-word-limit />
          </el-form-item>

          <el-form-item label="风格描述" prop="description">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="3"
              placeholder="描述这个风格的特点..."
              maxlength="500"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="目标风格" prop="target_style">
            <el-input v-model="form.target_style" placeholder="例如：幽默、学术、简洁" />
          </el-form-item>
        </el-form>
      </el-card>

      <!-- Base Model Selection -->
      <el-card class="form-section">
        <template #header>
          <div class="section-header">
            <el-icon><Cpu /></el-icon>
            <span>底座模型</span>
          </div>
        </template>

        <el-form :model="form" label-width="100px">
          <el-form-item label="选择模型" prop="base_model">
            <el-radio-group v-model="form.base_model">
              <el-radio-button label="llama-2-3b">LLaMA-2-3B</el-radio-button>
              <el-radio-button label="chatglm3-6b">ChatGLM3-6B</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- Training Text -->
      <el-card class="form-section">
        <template #header>
          <div class="section-header">
            <el-icon><Document /></el-icon>
            <span>训练文本</span>
            <span class="hint">（最少100字符，推荐1万-5万字）</span>
          </div>
        </template>

        <div class="text-input-area">
          <el-upload
            class="upload-area"
            drag
            action=""
            :auto-upload="false"
            :show-file-list="true"
            :on-change="handleFileChange"
            :limit="1"
            accept=".txt,.md,.docx"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              拖拽文件到此处或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 .txt, .md, .docx 格式，单文件不超过 10MB
              </div>
            </template>
          </el-upload>

          <div class="or-divider">或</div>

          <el-input
            v-model="form.training_text"
            type="textarea"
            :rows="8"
            placeholder="直接输入训练文本..."
            resize="none"
          />

          <div class="text-stats">
            已输入 {{ form.training_text.length.toLocaleString() }} 字符
            <span v-if="estimatedTokens > 0">，预估 {{ estimatedTokens.toLocaleString() }} tokens</span>
          </div>
        </div>
      </el-card>

      <!-- Training Config -->
      <el-card class="form-section">
        <template #header>
          <div class="section-header">
            <el-icon><Setting /></el-icon>
            <span>训练参数</span>
          </div>
        </template>

        <el-form :model="form.config" label-width="120px">
          <el-form-item label="学习率">
            <el-slider v-model="form.config.learning_rate" :min="0.00001" :max="0.001" :step="0.00001" show-stops />
            <span class="param-value">{{ form.config.learning_rate }}</span>
          </el-form-item>

          <el-form-item label="训练轮数">
            <el-slider v-model="form.config.num_epochs" :min="1" :max="10" show-stops />
            <span class="param-value">{{ form.config.num_epochs }} 轮</span>
          </el-form-item>

          <el-form-item label="批次大小">
            <el-radio-group v-model="form.config.batch_size">
              <el-radio-button :label="2">2</el-radio-button>
              <el-radio-button :label="4">4</el-radio-button>
              <el-radio-button :label="8">8</el-radio-button>
              <el-radio-button :label="16">16</el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-form-item label="最大序列长度">
            <el-slider v-model="form.config.max_length" :min="128" :max="2048" :step="128" show-stops />
            <span class="param-value">{{ form.config.max_length }} tokens</span>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- Submit Button -->
      <div class="submit-section">
        <el-button
          type="primary"
          size="large"
          :icon="VideoPlay"
          :loading="loading"
          :disabled="!canSubmit"
          @click="startTraining"
        >
          开始训练
        </el-button>
        <el-button size="large" @click="resetForm">重置</el-button>
      </div>

      <!-- Progress Monitor (when training) -->
      <ProgressMonitor
        v-if="currentTask"
        :task="currentTask"
        @close="currentTask = null"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useStyleStore } from '@/stores/style'
import { useTaskStore } from '@/stores/task'
import {
  InfoFilled,
  Cpu,
  Document,
  Setting,
  VideoPlay,
  UploadFilled
} from '@element-plus/icons-vue'
import ProgressMonitor from '@/components/Training/ProgressMonitor.vue'

const router = useRouter()
const styleStore = useStyleStore()
const taskStore = useTaskStore()

const formRef = ref(null)
const loading = ref(false)
const currentTask = ref(null)

const form = reactive({
  name: '',
  description: '',
  target_style: '',
  base_model: 'llama-2-3b',
  training_text: '',
  config: {
    learning_rate: 0.0002,
    num_epochs: 3,
    batch_size: 4,
    max_length: 512
  }
})

const rules = {
  name: [
    { required: true, message: '请输入风格名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  target_style: [
    { required: true, message: '请输入目标风格', trigger: 'blur' }
  ]
}

const estimatedTokens = computed(() => {
  return Math.round(form.training_text.length / 2)
})

const canSubmit = computed(() => {
  return form.name &&
         form.target_style &&
         form.training_text.length >= 100 &&
         !loading.value
})

function handleFileChange(file) {
  const reader = new FileReader()
  reader.onload = (e) => {
    form.training_text = e.target.result
    ElMessage.success(`文件 "${file.name}" 读取成功`)
  }
  reader.onerror = () => {
    ElMessage.error('文件读取失败')
  }
  reader.readAsText(file.raw)
}

async function startTraining() {
  console.log('[StyleTraining] Starting training...')
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    console.log('[StyleTraining] Form validation failed')
    return
  }

  loading.value = true

  try {
    // 1. Create style first
    console.log('[StyleTraining] Step 1: Creating style...')
    const styleData = {
      name: form.name,
      description: form.description,
      target_style: form.target_style,
      base_model: form.base_model
    }
    console.log('[StyleTraining] Style data:', styleData)
    const style = await styleStore.createStyle(styleData)
    console.log('[StyleTraining] Style created:', style.id)

    // 2. Create training task
    console.log('[StyleTraining] Step 2: Creating training task...')
    const taskData = {
      style_id: style.id,
      base_model: form.base_model,
      training_text: form.training_text,
      config: form.config
    }
    console.log('[StyleTraining] Task data:', {
      style_id: taskData.style_id,
      base_model: taskData.base_model,
      training_text_length: taskData.training_text.length,
      config: taskData.config
    })
    const task = await taskStore.createTask(taskData)
    console.log('[StyleTraining] Task created:', task.id, 'Status:', task.status)

    ElMessage.success('训练任务已创建')
    currentTask.value = task

    // 3. Show progress monitor
    console.log('[StyleTraining] Step 3: Connecting WebSocket for progress...')
    taskStore.connectToTaskProgress(task.id, (data) => {
      console.log('[StyleTraining] Progress update received:', {
        type: data.type,
        status: data.data?.status,
        progress: data.data?.progress
      })
      if (data.type === 'progress') {
        Object.assign(task, data.data)
      }
    })

  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

function resetForm() {
  formRef.value?.resetFields()
  form.training_text = ''
}
</script>

<style scoped>
.page-container {
  max-width: 800px;
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

.form-section {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.hint {
  font-size: 13px;
  color: #909399;
  font-weight: normal;
  margin-left: 8px;
}

.text-input-area {
  padding: 20px 0;
}

.upload-area {
  width: 100%;
}

.or-divider {
  text-align: center;
  color: #909399;
  margin: 20px 0;
  position: relative;
}

.or-divider::before,
.or-divider::after {
  content: '';
  position: absolute;
  top: 50%;
  width: 40%;
  height: 1px;
  background: #e4e7ed;
}

.or-divider::before { left: 0; }
.or-divider::after { right: 0; }

.text-stats {
  text-align: right;
  color: #909399;
  font-size: 13px;
  margin-top: 8px;
}

.param-value {
  margin-left: 12px;
  color: #409eff;
  font-weight: 500;
}

.submit-section {
  display: flex;
  justify-content: center;
  gap: 16px;
  padding: 20px;
}
</style>
