<template>
  <div class="training-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-title">
          <div class="title-icon">
            <el-icon :size="28"><Cpu /></el-icon>
          </div>
          <div class="title-text">
            <h1>风格模型训练</h1>
            <p>创建自定义风格并训练专属模型</p>
          </div>
        </div>
      </div>
    </div>

    <div class="training-layout">
      <!-- Left: Form Steps -->
      <div class="training-form">
        <!-- Progress Steps -->
        <div class="steps-nav">
          <div
            v-for="(step, index) in steps"
            :key="step.key"
            :class="['step-item', { active: currentStep >= index, current: currentStep === index }]"
          >
            <div class="step-number">
              <el-icon v-if="currentStep > index" :size="16"><Check /></el-icon>
              <span v-else>{{ index + 1 }}</span>
            </div>
            <span class="step-label">{{ step.label }}</span>
          </div>
        </div>

        <!-- Step 1: Basic Info -->
        <div v-show="currentStep === 0" class="step-content">
          <div class="form-card">
            <div class="card-header">
              <el-icon :size="24" color="#667eea"><InfoFilled /></el-icon>
              <div class="header-text">
                <h3>基本信息</h3>
                <p>定义您的风格名称和目标</p>
              </div>
            </div>

            <el-form :model="form" label-position="top" :rules="rules" ref="formRef">
              <el-form-item label="风格名称" prop="name">
                <el-input
                  v-model="form.name"
                  placeholder="例如：幽默风趣风格"
                  size="large"
                  maxlength="50"
                  show-word-limit
                />
              </el-form-item>

              <el-form-item label="目标风格" prop="target_style">
                <el-select
                  v-model="form.target_style"
                  placeholder="选择或输入目标风格"
                  size="large"
                  filterable
                  allow-create
                  default-first-option
                >
                  <el-option label="幽默风趣" value="幽默风趣" />
                  <el-option label="学术严谨" value="学术严谨" />
                  <el-option label="简洁明了" value="简洁明了" />
                  <el-option label="文艺优美" value="文艺优美" />
                  <el-option label="商务正式" value="商务正式" />
                  <el-option label="亲切友好" value="亲切友好" />
                </el-select>
              </el-form-item>

              <el-form-item label="风格描述" prop="description">
                <el-input
                  v-model="form.description"
                  type="textarea"
                  :rows="4"
                  placeholder="描述这个风格的特点、适用场景..."
                  maxlength="500"
                  show-word-limit
                />
              </el-form-item>
            </el-form>
          </div>
        </div>

        <!-- Step 2: Model Selection -->
        <div v-show="currentStep === 1" class="step-content">
          <div class="form-card">
            <div class="card-header">
              <el-icon :size="24" color="#667eea"><SetUp /></el-icon>
              <div class="header-text">
                <h3>选择底座模型</h3>
                <p>选择作为训练基础的预训练模型</p>
              </div>
            </div>

            <div class="model-options">
              <div
                v-for="model in models"
                :key="model.id"
                :class="['model-card', { selected: form.base_model === model.id }]"
                @click="form.base_model = model.id"
              >
                <div class="model-badge" :class="model.type">
                  {{ model.type === 'llama' ? 'LLaMA' : 'ChatGLM' }}
                </div>
                <div class="model-icon">
                  <el-icon :size="32"><component :is="model.icon" /></el-icon>
                </div>
                <h4>{{ model.name }}</h4>
                <p>{{ model.description }}</p>
                <div class="model-specs">
                  <span class="spec">
                    <el-icon><DataLine /></el-icon>
                    {{ model.params }}
                  </span>
                  <span class="spec">
                    <el-icon><Timer /></el-icon>
                    {{ model.speed }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Step 3: Training Data -->
        <div v-show="currentStep === 2" class="step-content">
          <div class="form-card">
            <div class="card-header">
              <el-icon :size="24" color="#667eea"><Document /></el-icon>
              <div class="header-text">
                <h3>训练数据</h3>
                <p>上传或输入示例文本用于训练</p>
              </div>
            </div>

            <div class="upload-section">
              <el-upload
                class="modern-upload"
                drag
                action=""
                :auto-upload="false"
                :show-file-list="true"
                :on-change="handleFileChange"
                :limit="1"
                accept=".txt,.md,.docx"
              >
                <div class="upload-content">
                  <div class="upload-icon">
                    <el-icon :size="48"><UploadFilled /></el-icon>
                  </div>
                  <div class="upload-text">
                    <h4>拖拽文件到此处</h4>
                    <p>或点击上传训练文本文件</p>
                    <span class="upload-hint">支持 .txt, .md, .docx 格式，不超过 10MB</span>
                  </div>
                </div>
              </el-upload>

              <div class="divider">
                <span>或者</span>
              </div>

              <div class="text-input-section">
                <div class="input-header">
                  <span class="input-label">直接输入文本</span>
                  <span class="char-count" :class="{ 'is-valid': form.training_text.length >= 100 }">
                    {{ form.training_text.length.toLocaleString() }} / 最少100字符
                  </span>
                </div>
                <el-input
                  v-model="form.training_text"
                  type="textarea"
                  :rows="8"
                  placeholder="在此粘贴您的训练文本...&#10;建议提供1万-5万字的示例文本，以获得更好的训练效果"
                  resize="none"
                  class="training-textarea"
                />
              </div>

              <div v-if="estimatedTokens > 0" class="token-estimate">
                <el-icon><InfoFilled /></el-icon>
                <span>预估 tokens: {{ estimatedTokens.toLocaleString() }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Step 4: Training Config -->
        <div v-show="currentStep === 3" class="step-content">
          <div class="form-card">
            <div class="card-header">
              <el-icon :size="24" color="#667eea"><Setting /></el-icon>
              <div class="header-text">
                <h3>训练参数</h3>
                <p>调整训练参数以优化模型效果</p>
              </div>
            </div>

            <div class="config-grid">
              <div class="config-item">
                <div class="config-label">
                  <span>训练轮数 (Epochs)</span>
                  <el-tooltip content="训练的轮数，更多轮数通常效果更好但需要更长时间" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </div>
                <div class="config-control">
                  <el-slider v-model="form.config.num_epochs" :min="1" :max="10" show-stops />
                  <span class="config-value">{{ form.config.num_epochs }} 轮</span>
                </div>
              </div>

              <div class="config-item">
                <div class="config-label">
                  <span>学习率 (Learning Rate)</span>
                  <el-tooltip content="控制模型学习的速度，过高可能导致不稳定" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </div>
                <div class="config-control">
                  <el-slider
                    v-model="form.config.learning_rate"
                    :min="0.00001"
                    :max="0.001"
                    :step="0.00001"
                    :format-tooltip="v => v.toExponential(2)"
                  />
                  <span class="config-value">{{ form.config.learning_rate.toExponential(2) }}</span>
                </div>
              </div>

              <div class="config-item">
                <div class="config-label">
                  <span>批次大小 (Batch Size)</span>
                  <el-tooltip content="每次训练的样本数量，更大需要更多显存" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </div>
                <div class="config-control">
                  <el-radio-group v-model="form.config.batch_size" size="large">
                    <el-radio-button :label="2">2</el-radio-button>
                    <el-radio-button :label="4">4</el-radio-button>
                    <el-radio-button :label="8">8</el-radio-button>
                    <el-radio-button :label="16">16</el-radio-button>
                  </el-radio-group>
                </div>
              </div>

              <div class="config-item">
                <div class="config-label">
                  <span>最大序列长度</span>
                  <el-tooltip content="输入文本的最大长度（tokens）" placement="top">
                    <el-icon><QuestionFilled /></el-icon>
                  </el-tooltip>
                </div>
                <div class="config-control">
                  <el-slider v-model="form.config.max_length" :min="128" :max="2048" :step="128" show-stops />
                  <span class="config-value">{{ form.config.max_length }} tokens</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Navigation Buttons -->
        <div class="form-actions">
          <el-button
            v-if="currentStep > 0"
            size="large"
            @click="currentStep--"
          >
            <el-icon><ArrowLeft /></el-icon>
            上一步
          </el-button>
          <el-button
            v-if="currentStep < steps.length - 1"
            type="primary"
            size="large"
            @click="nextStep"
          >
            下一步
            <el-icon><ArrowRight /></el-icon>
          </el-button>
          <el-button
            v-else
            type="primary"
            size="large"
            :icon="VideoPlay"
            :loading="loading"
            :disabled="!canSubmit"
            class="submit-btn"
            @click="startTraining"
          >
            开始训练
          </el-button>
        </div>
      </div>

      <!-- Right: Preview Card -->
      <div class="preview-panel">
        <div class="preview-card">
          <div class="preview-header">
            <el-icon :size="20"><View /></el-icon>
            <span>训练预览</span>
          </div>

          <div class="preview-content">
            <div class="preview-section">
              <span class="preview-label">风格名称</span>
              <span class="preview-value">{{ form.name || '未设置' }}</span>
            </div>

            <div class="preview-section">
              <span class="preview-label">目标风格</span>
              <span class="preview-value">{{ form.target_style || '未设置' }}</span>
            </div>

            <div class="preview-section">
              <span class="preview-label">底座模型</span>
              <span class="preview-value">{{ getModelName(form.base_model) }}</span>
            </div>

            <div class="preview-section">
              <span class="preview-label">训练数据</span>
              <span class="preview-value">{{ formatDataSize(form.training_text.length) }}</span>
            </div>

            <div class="preview-section">
              <span class="preview-label">预估时间</span>
              <span class="preview-value highlight">{{ estimatedTime }}</span>
            </div>
          </div>

          <div class="preview-tips">
            <el-icon :size="16"><InfoFilled /></el-icon>
            <p>训练完成后，系统将自动保存模型并更新风格状态</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Progress Monitor -->
    <ProgressMonitor
      v-if="currentTask"
      :task="currentTask"
      @close="currentTask = null"
    />
  </div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useStyleStore } from '@/stores/style'
import { useTaskStore } from '@/stores/task'
import { ElMessage } from 'element-plus'
import {
  Cpu,
  InfoFilled,
  SetUp,
  Document,
  Setting,
  VideoPlay,
  UploadFilled,
  Check,
  ArrowLeft,
  ArrowRight,
  View,
  DataLine,
  Timer,
  QuestionFilled
} from '@element-plus/icons-vue'
import ProgressMonitor from '@/components/Training/ProgressMonitor.vue'

const router = useRouter()
const styleStore = useStyleStore()
const taskStore = useTaskStore()

const currentStep = ref(0)
const formRef = ref(null)
const loading = ref(false)
const currentTask = ref(null)

const steps = [
  { key: 'basic', label: '基本信息' },
  { key: 'model', label: '模型选择' },
  { key: 'data', label: '训练数据' },
  { key: 'config', label: '训练参数' }
]

const models = [
  {
    id: 'llama-2-3b',
    name: 'LLaMA-2-3B',
    type: 'llama',
    icon: 'Cpu',
    description: 'Meta开源的基础模型，性能均衡',
    params: '3B参数',
    speed: '速度较快'
  },
  {
    id: 'chatglm3-6b',
    name: 'ChatGLM3-6B',
    type: 'chatglm',
    icon: 'ChatDotRound',
    description: '清华ChatGLM系列，中文优化',
    params: '6B参数',
    speed: '效果更好'
  }
]

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
    { required: true, message: '请输入目标风格', trigger: 'change' }
  ]
}

const estimatedTokens = computed(() => {
  return Math.round(form.training_text.length / 2)
})

const estimatedTime = computed(() => {
  const baseTime = 5 // minutes
  const epochTime = form.config.num_epochs * 3
  return `约 ${baseTime + epochTime} 分钟`
})

const canSubmit = computed(() => {
  return form.name &&
         form.target_style &&
         form.training_text.length >= 100 &&
         !loading.value
})

function getModelName(id) {
  const model = models.find(m => m.id === id)
  return model ? model.name : id
}

function formatDataSize(length) {
  if (length === 0) return '未设置'
  if (length < 1000) return `${length} 字符`
  return `${(length / 1000).toFixed(1)}K 字符`
}

async function nextStep() {
  if (currentStep.value === 0) {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
  }
  if (currentStep.value < steps.length - 1) {
    currentStep.value++
  }
}

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
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    currentStep.value = 0
    return
  }

  if (form.training_text.length < 100) {
    ElMessage.warning('训练文本至少需要100字符')
    currentStep.value = 2
    return
  }

  loading.value = true

  try {
    // 1. Create style
    const styleData = {
      name: form.name,
      description: form.description,
      target_style: form.target_style,
      base_model: form.base_model
    }
    const style = await styleStore.createStyle(styleData)

    // 2. Create training task
    const taskData = {
      style_id: style.id,
      base_model: form.base_model,
      training_text: form.training_text,
      config: form.config
    }
    const task = await taskStore.createTask(taskData)

    ElMessage.success('训练任务已创建')
    currentTask.value = task

    // 3. Connect WebSocket
    taskStore.connectToTaskProgress(task.id, (data) => {
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
</script>

<style scoped>
.training-page {
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
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 0 20px rgba(16, 185, 129, 0.3);
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
.training-layout {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 24px;
}

/* Steps Nav */
.steps-nav {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  background: var(--bg-card);
  padding: 16px;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
}

.step-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  opacity: 0.5;
}

.step-item.active {
  opacity: 1;
}

.step-item.current {
  background: rgba(102, 126, 234, 0.1);
}

.step-number {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.step-item.active .step-number {
  background: var(--primary-gradient);
  color: white;
}

.step-item.current .step-number {
  box-shadow: var(--shadow-glow);
}

.step-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
}

.step-item.active .step-label {
  color: var(--text-primary);
}

/* Form Card */
.form-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 28px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
}

.header-text h3 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px;
}

.header-text p {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

/* Model Options */
.model-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.model-card {
  position: relative;
  padding: 24px;
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  border: 2px solid transparent;
  cursor: pointer;
  transition: all var(--transition-normal);
}

.model-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
}

.model-card.selected {
  border-color: var(--primary-color);
  background: rgba(102, 126, 234, 0.05);
  box-shadow: var(--shadow-glow);
}

.model-badge {
  position: absolute;
  top: 16px;
  right: 16px;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.model-badge.llama {
  background: rgba(102, 126, 234, 0.1);
  color: var(--primary-color);
}

.model-badge.chatglm {
  background: rgba(16, 185, 129, 0.1);
  color: var(--success-color);
}

.model-icon {
  width: 56px;
  height: 56px;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
  margin-bottom: 16px;
}

.model-card h4 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.model-card p {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0 0 16px;
  line-height: 1.5;
}

.model-specs {
  display: flex;
  gap: 16px;
}

.spec {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

/* Upload Section */
.upload-section {
  padding: 8px 0;
}

.modern-upload :deep(.el-upload-dragger) {
  width: 100%;
  padding: 48px;
  background: var(--bg-secondary);
  border: 2px dashed var(--border-color);
  border-radius: var(--radius-lg);
  transition: all var(--transition-fast);
}

.modern-upload :deep(.el-upload-dragger:hover) {
  border-color: var(--primary-color);
  background: rgba(102, 126, 234, 0.05);
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.upload-icon {
  width: 80px;
  height: 80px;
  background: var(--bg-card);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
  margin-bottom: 20px;
  box-shadow: var(--shadow-sm);
}

.upload-text h4 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.upload-text p {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0 0 8px;
}

.upload-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.divider {
  display: flex;
  align-items: center;
  margin: 28px 0;
  color: var(--text-muted);
  font-size: 14px;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-color);
}

.divider span {
  padding: 0 16px;
}

.text-input-section {
  background: var(--bg-secondary);
  padding: 20px;
  border-radius: var(--radius-lg);
}

.input-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.input-label {
  font-weight: 600;
  color: var(--text-primary);
}

.char-count {
  font-size: 13px;
  color: var(--text-muted);
}

.char-count.is-valid {
  color: var(--success-color);
  font-weight: 600;
}

.training-textarea :deep(.el-textarea__inner) {
  background: var(--bg-card);
  border-color: var(--border-color);
  border-radius: var(--radius-md);
}

.token-estimate {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding: 12px 16px;
  background: rgba(59, 130, 246, 0.1);
  border-radius: var(--radius-md);
  color: var(--info-color);
  font-size: 13px;
}

/* Config Grid */
.config-grid {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.config-item {
  padding: 20px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.config-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.config-label .el-icon {
  color: var(--text-muted);
  cursor: help;
}

.config-control {
  display: flex;
  align-items: center;
  gap: 20px;
}

.config-control .el-slider {
  flex: 1;
}

.config-value {
  min-width: 100px;
  font-weight: 600;
  color: var(--primary-color);
  text-align: right;
}

/* Form Actions */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

.submit-btn {
  padding: 12px 32px;
  font-weight: 600;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border: none;
}

/* Preview Panel */
.preview-panel {
  position: sticky;
  top: 24px;
}

.preview-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-color);
  overflow: hidden;
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  font-weight: 600;
  color: var(--text-primary);
}

.preview-content {
  padding: 20px;
}

.preview-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
}

.preview-section:last-child {
  border-bottom: none;
}

.preview-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.preview-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.preview-value.highlight {
  color: var(--primary-color);
  font-weight: 600;
}

.preview-tips {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 16px 20px;
  background: rgba(245, 158, 11, 0.1);
  border-top: 1px solid var(--border-color);
  color: var(--warning-color);
  font-size: 13px;
  line-height: 1.5;
}

.preview-tips .el-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.preview-tips p {
  margin: 0;
}

/* Responsive */
@media (max-width: 1200px) {
  .training-layout {
    grid-template-columns: 1fr;
  }

  .preview-panel {
    position: static;
    order: -1;
  }
}

/* Animations */
.step-content {
  animation: fadeIn 0.4s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>
