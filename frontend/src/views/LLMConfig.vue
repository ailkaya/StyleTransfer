<template>
  <div class="page-container">
    <div class="page-header">
      <h1>系统配置</h1>
      <p>配置大模型API参数</p>
    </div>

    <div class="config-container">
      <el-card class="config-card">
        <template #header>
          <div class="card-header">
            <span>大模型API配置</span>
            <el-tag v-if="configStore.llmConfig.has_api_key" type="success">已配置</el-tag>
            <el-tag v-else type="warning">未配置</el-tag>
          </div>
        </template>

        <el-form :model="form" label-width="120px" :rules="rules" ref="formRef">
          <el-form-item label="API基础URL" prop="base_url">
            <el-input
              v-model="form.base_url"
              placeholder="https://api.openai.com/v1"
            />
            <div class="form-hint">支持OpenAI格式API的基础URL</div>
          </el-form-item>

          <el-form-item label="模型名称" prop="model_name">
            <el-input
              v-model="form.model_name"
              placeholder="gpt-3.5-turbo"
            />
          </el-form-item>

          <el-form-item label="API密钥" prop="api_key">
            <el-input
              v-model="form.api_key"
              type="password"
              placeholder="sk-..."
              show-password
            />
            <div class="form-hint">密钥仅存储于后端，不会暴露给前端</div>
          </el-form-item>
        </el-form>

        <div class="form-actions">
          <el-button
            type="primary"
            :icon="Check"
            :loading="configStore.verifying"
            @click="verifyConnection"
          >
            测试连接
          </el-button>

          <el-button
            type="success"
            :icon="Document"
            :loading="configStore.loading"
            @click="saveConfig"
          >
            保存配置
          </el-button>
        </div>
      </el-card>

      <el-card class="info-card">
        <template #header>
          <div class="card-header">
            <span>使用说明</span>
          </div>
        </template>

        <div class="info-content">
          <h4>支持的API格式</h4>
          <p>本系统使用OpenAI兼容的API格式，支持以下服务：</p>
          <ul>
            <li>OpenAI API</li>
            <li>Anthropic API (通过转换)</li>
            <li>Azure OpenAI Service</li>
            <li>本地部署的模型 (如 vLLM, Text Generation Inference)</li>
            <li>第三方OpenAI兼容服务</li>
          </ul>

          <h4>配置示例</h4>
          <div class="code-block">
            <p><strong>OpenAI:</strong></p>
            <p>Base URL: https://api.openai.com/v1</p>
            <p>Model: gpt-3.5-turbo</p>
          </div>

          <div class="code-block">
            <p><strong>本地vLLM:</strong></p>
            <p>Base URL: http://localhost:8000/v1</p>
            <p>Model: your-model-name</p>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useConfigStore } from '@/stores/config'
import { Check, Document } from '@element-plus/icons-vue'

const configStore = useConfigStore()
const formRef = ref(null)

const form = reactive({
  base_url: '',
  model_name: '',
  api_key: ''
})

const rules = {
  base_url: [
    { required: true, message: '请输入API基础URL', trigger: 'blur' }
  ],
  model_name: [
    { required: true, message: '请输入模型名称', trigger: 'blur' }
  ],
  api_key: [
    { required: true, message: '请输入API密钥', trigger: 'blur' }
  ]
}

onMounted(async () => {
  await configStore.fetchLLMConfig()
  form.base_url = configStore.llmConfig.base_url
  form.model_name = configStore.llmConfig.model_name
  // api_key is not returned for security reasons
})

async function verifyConnection() {
  try {
    await configStore.verifyLLMConnection()
    ElMessage.success('连接测试成功')
  } catch (error) {
    ElMessage.error('连接测试失败: ' + error.message)
  }
}

async function saveConfig() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  try {
    await configStore.updateLLMConfig(form)
    ElMessage.success('配置保存成功')
  } catch (error) {
    ElMessage.error(error.message)
  }
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

.config-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.form-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  padding-top: 20px;
  border-top: 1px solid #e4e7ed;
}

.info-content h4 {
  margin: 16px 0 8px;
  color: #1a1a2e;
}

.info-content h4:first-child {
  margin-top: 0;
}

.info-content p {
  color: #606266;
  margin-bottom: 8px;
}

.info-content ul {
  color: #606266;
  padding-left: 20px;
  margin-bottom: 16px;
}

.info-content li {
  margin-bottom: 4px;
}

.code-block {
  background: #f5f7fa;
  padding: 12px 16px;
  border-radius: 4px;
  margin-bottom: 12px;
}

.code-block p {
  margin-bottom: 4px;
  font-size: 13px;
}

.code-block strong {
  color: #1a1a2e;
}
</style>
