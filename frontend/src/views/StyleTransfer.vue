<template>
  <div class="page-container">
    <div class="page-header">
      <h1>风格转化</h1>
      <p>将您的文本转换为特定风格</p>
    </div>

    <div class="transfer-container">
      <!-- Style Selector -->
      <div class="style-selector">
        <el-select
          v-model="selectedStyleId"
          placeholder="选择目标风格"
          size="large"
          style="width: 100%"
          @change="onStyleChange"
        >
          <el-option
            v-for="style in styleStore.availableStyles"
            :key="style.id"
            :label="style.name"
            :value="style.id"
          >
            <div class="style-option">
              <span>{{ style.name }}</span>
              <el-tag size="small" type="info">{{ style.target_style }}</el-tag>
            </div>
          </el-option>
        </el-select>
      </div>

      <div v-if="selectedStyleId" class="chat-container">
        <!-- Chat Messages -->
        <div ref="messagesContainer" class="messages-area">
          <div v-if="messageStore.messages.length === 0" class="empty-state">
            <el-icon :size="48" color="#909399"><ChatDotRound /></el-icon>
            <p>开始一个新的对话</p>
            <p class="hint">输入原文和转换需求，AI将为您转换文本风格</p>
          </div>

          <div
            v-for="msg in messageStore.messages"
            :key="msg.id"
            :class="['message', msg.role]"
          >
            <div class="message-avatar">
              <el-avatar
                :size="36"
                :icon="msg.role === 'user' ? User : ChatDotRound"
                :class="msg.role"
              />
            </div>
            <div class="message-content">
              <div v-if="msg.original_text" class="original-text">
                <div class="label">原文：</div>
                <div class="text">{{ msg.original_text.substring(0, 100) }}...</div>
              </div>
              <div v-if="msg.requirement" class="requirement">
                <div class="label">需求：</div>
                <div class="text">{{ msg.requirement }}</div>
              </div>
              <div class="response-text">{{ msg.content }}</div>
              <div class="message-time">{{ formatTime(msg.created_at) }}</div>
            </div>
          </div>

          <div v-if="messageStore.sending" class="message assistant loading">
            <div class="message-avatar">
              <el-avatar :size="36" :icon="ChatDotRound" class="assistant" />
            </div>
            <div class="message-content">
              <el-skeleton :rows="2" animated />
            </div>
          </div>
        </div>

        <!-- Input Area -->
        <div class="input-area">
          <!-- Original Text Input -->
          <div class="input-section">
            <div class="input-label">
              <el-icon><Document /></el-icon>
              <span>原文内容</span>
              <el-upload
                class="upload-btn"
                action=""
                :auto-upload="false"
                :show-file-list="false"
                :on-change="handleFileChange"
                accept=".txt,.md,.docx"
              >
                <el-button link type="primary" :icon="Upload">
                  上传文件
                </el-button>
              </el-upload>
            </div>
            <el-input
              v-model="originalText"
              type="textarea"
              :rows="4"
              placeholder="请输入或上传需要转换风格的文本..."
              resize="none"
            />
            <div class="input-hint">已输入 {{ originalText.length }} 字符</div>
          </div>

          <!-- Requirement Input -->
          <div class="input-section">
            <div class="input-label">
              <el-icon><EditPen /></el-icon>
              <span>转换需求</span>
            </div>
            <el-input
              v-model="requirement"
              type="textarea"
              :rows="2"
              :placeholder="`请描述您对转换的具体需求，例如：转换为${currentStyle?.target_style || '目标'}风格...`"
              resize="none"
            />
          </div>

          <!-- Send Button -->
          <div class="send-section">
            <el-button
              type="primary"
              size="large"
              :icon="Position"
              :loading="messageStore.sending"
              :disabled="!canSend"
              @click="sendMessage"
            >
              开始转换
            </el-button>
            <el-button
              link
              :icon="Delete"
              @click="clearHistory"
            >
              清空历史
            </el-button>
          </div>
        </div>
      </div>

      <div v-else class="empty-selection">
        <el-empty description="请先选择一个目标风格">
          <el-button type="primary" @click="$router.push('/style-management')">
            去创建风格
          </el-button>
        </el-empty>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useStyleStore } from '@/stores/style'
import { useMessageStore } from '@/stores/message'
import {
  ChatDotRound,
  User,
  Document,
  EditPen,
  Position,
  Delete,
  Upload
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const styleStore = useStyleStore()
const messageStore = useMessageStore()

const selectedStyleId = ref('')
const originalText = ref('')
const requirement = ref('')
const messagesContainer = ref(null)

const currentStyle = computed(() =>
  styleStore.getStyleById(selectedStyleId.value)
)

const canSend = computed(() =>
  selectedStyleId.value &&
  originalText.value.trim() &&
  requirement.value.trim() &&
  !messageStore.sending
)

// Load available styles on mount
styleStore.fetchStyles({ page_size: 100 })

// Load messages when style changes
async function onStyleChange() {
  messageStore.clearLocalMessages()
  if (selectedStyleId.value) {
    await messageStore.fetchMessages(selectedStyleId.value)
    scrollToBottom()
  }
}

async function sendMessage() {
  if (!canSend.value) return

  const data = {
    original_text: originalText.value.trim(),
    requirement: requirement.value.trim()
  }

  try {
    await messageStore.sendMessage(selectedStyleId.value, data)
    originalText.value = ''
    requirement.value = ''
    nextTick(() => scrollToBottom())
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function clearHistory() {
  try {
    await ElMessageBox.confirm('确定要清空当前风格的所有历史记录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await messageStore.clearMessages(selectedStyleId.value)
    ElMessage.success('历史记录已清空')
  } catch {
    // User cancelled
  }
}

function handleFileChange(file) {
  const reader = new FileReader()
  reader.onload = (e) => {
    originalText.value = e.target.result
    ElMessage.success('文件读取成功')
  }
  reader.onerror = () => {
    ElMessage.error('文件读取失败')
  }
  reader.readAsText(file.raw)
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

function formatTime(time) {
  return dayjs(time).format('MM-DD HH:mm')
}

// Watch for new messages and scroll
watch(() => messageStore.messages.length, () => {
  nextTick(() => scrollToBottom())
})
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

.transfer-container {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.style-selector {
  padding: 20px;
  border-bottom: 1px solid #e4e7ed;
}

.style-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 200px);
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f8f9fa;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}

.empty-state .hint {
  font-size: 14px;
  margin-top: 8px;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar .el-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.message-avatar .el-avatar.user {
  background: #409eff;
}

.message-content {
  max-width: 70%;
  padding: 12px 16px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.message.user .message-content {
  background: #ecf5ff;
}

.original-text, .requirement {
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px dashed #dcdfe6;
}

.label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.text {
  font-size: 13px;
  color: #606266;
}

.response-text {
  font-size: 14px;
  line-height: 1.6;
  color: #303133;
  white-space: pre-wrap;
}

.message-time {
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 8px;
  text-align: right;
}

.input-area {
  padding: 20px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
}

.input-section {
  margin-bottom: 16px;
}

.input-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-weight: 500;
  color: #303133;
}

.upload-btn {
  margin-left: auto;
}

.input-hint {
  font-size: 12px;
  color: #909399;
  text-align: right;
  margin-top: 4px;
}

.send-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid #e4e7ed;
}

.empty-selection {
  padding: 60px 20px;
}

.loading .message-content {
  min-width: 200px;
}
</style>
