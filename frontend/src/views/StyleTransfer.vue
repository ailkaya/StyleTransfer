<template>
  <div class="style-transfer-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-title">
          <div class="title-icon">
            <el-icon :size="28"><Magic /></el-icon>
          </div>
          <div class="title-text">
            <h1>智能风格转换</h1>
            <p>将您的文本转换为独特的目标风格</p>
          </div>
        </div>
        <div class="header-actions">
          <el-select
            v-model="selectedStyleId"
            placeholder="选择目标风格"
            size="large"
            class="style-select"
            @change="onStyleChange"
          >
            <template #prefix>
              <el-icon><Collection /></el-icon>
            </template>
            <el-option
              v-for="style in styleStore.availableStyles"
              :key="style.id"
              :label="style.name"
              :value="style.id"
            >
              <div class="style-option">
                <div class="style-info">
                  <span class="style-name">{{ style.name }}</span>
                  <span class="style-desc">{{ style.description || '暂无描述' }}</span>
                </div>
                <el-tag size="small" type="primary" effect="light">{{ style.target_style }}</el-tag>
              </div>
            </el-option>
          </el-select>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="main-container">
      <div v-if="selectedStyleId" class="chat-layout">
        <!-- Messages Area -->
        <div ref="messagesContainer" class="messages-container">
          <div v-if="messageStore.messages.length === 0" class="welcome-state">
            <div class="welcome-card">
              <div class="welcome-icon">
                <el-icon :size="64"><ChatDotRound /></el-icon>
              </div>
              <h2>开始风格转换</h2>
              <p>输入原文和转换需求，AI将为您生成目标风格的文本</p>
              <div class="quick-tips">
                <div class="tip-item">
                  <el-icon><Document /></el-icon>
                  <span>支持长文本输入</span>
                </div>
                <div class="tip-item">
                  <el-icon><Upload /></el-icon>
                  <span>可上传文件</span>
                </div>
                <div class="tip-item">
                  <el-icon><Clock /></el-icon>
                  <span>历史记录自动保存</span>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="messages-list">
            <div
              v-for="(msg, index) in messageStore.messages"
              :key="msg.id"
              :class="['message-wrapper', msg.role]"
              :style="{ animationDelay: `${index * 0.1}s` }"
            >
              <div class="message-bubble">
                <div class="message-header">
                  <div class="message-avatar" :class="msg.role">
                    <el-icon :size="18">
                      <User v-if="msg.role === 'user'" />
                      <Magic v-else />
                    </el-icon>
                  </div>
                  <span class="message-role">{{ msg.role === 'user' ? '我' : 'AI助手' }}</span>
                  <span class="message-time">{{ formatTime(msg.created_at) }}</span>
                </div>

                <div class="message-body">
                  <!-- User Input Summary -->
                  <div v-if="msg.original_text || msg.requirement" class="input-summary">
                    <div v-if="msg.original_text" class="summary-item">
                      <span class="summary-label">原文</span>
                      <span class="summary-text">{{ msg.original_text }}</span>
                    </div>
                    <div v-if="msg.requirement" class="summary-item">
                      <span class="summary-label">需求</span>
                      <span class="summary-text requirement">{{ msg.requirement }}</span>
                    </div>
                  </div>

                  <!-- AI Response -->
                  <div class="response-content">
                    {{ msg.content }}
                  </div>
                </div>

                <div class="message-actions">
                  <el-button
                    v-if="msg.role === 'assistant'"
                    link
                    size="small"
                    :icon="CopyDocument"
                    @click="copyText(msg.content)"
                  >
                    复制
                  </el-button>
                  <el-button
                    link
                    size="small"
                    :icon="Delete"
                    @click="deleteMessage(msg.id)"
                  >
                    删除
                  </el-button>
                </div>
              </div>
            </div>

            <!-- Loading State -->
            <div v-if="messageStore.sending" class="message-wrapper assistant loading">
              <div class="message-bubble">
                <div class="message-header">
                  <div class="message-avatar assistant">
                    <el-icon :size="18"><Magic /></el-icon>
                  </div>
                  <span class="message-role">AI助手</span>
                  <span class="message-status">正在思考...</span>
                </div>
                <div class="message-body">
                  <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Input Area -->
        <div class="input-panel">
          <div class="input-container">
            <div class="input-tabs">
              <div
                v-for="tab in inputTabs"
                :key="tab.key"
                :class="['input-tab', { active: activeTab === tab.key }]"
                @click="activeTab = tab.key"
              >
                <el-icon :size="16"><component :is="tab.icon" /></el-icon>
                <span>{{ tab.label }}</span>
              </div>
            </div>

            <div class="input-fields">
              <!-- Original Text Input -->
              <div v-show="activeTab === 'text'" class="input-field">
                <div class="field-header">
                  <span class="field-label">
                    <el-icon><Document /></el-icon>
                    原文内容
                  </span>
                  <div class="field-actions">
                    <el-upload
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
                    <span class="char-count">{{ originalText.length }} 字符</span>
                  </div>
                </div>
                <el-input
                  v-model="originalText"
                  type="textarea"
                  :rows="6"
                  placeholder="请输入需要转换风格的文本..."
                  resize="none"
                  class="custom-textarea"
                />
              </div>

              <!-- Requirement Input -->
              <div v-show="activeTab === 'requirement'" class="input-field">
                <div class="field-header">
                  <span class="field-label">
                    <el-icon><EditPen /></el-icon>
                    转换需求
                  </span>
                </div>
                <el-input
                  v-model="requirement"
                  type="textarea"
                  :rows="6"
                  :placeholder="`描述您对转换的具体需求，例如：转换为${currentStyle?.target_style || '目标'}风格，保持原文意思的同时增加文采...`"
                  resize="none"
                  class="custom-textarea"
                />
              </div>
            </div>

            <div class="input-footer">
              <el-button
                link
                :icon="Delete"
                @click="clearHistory"
              >
                清空对话
              </el-button>
              <el-button
                type="primary"
                size="large"
                :icon="Position"
                :loading="messageStore.sending"
                :disabled="!canSend"
                class="send-button"
                @click="sendMessage"
              >
                开始转换
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="empty-state">
        <div class="empty-card">
          <div class="empty-illustration">
            <el-icon :size="80" color="#cbd5e1"><Collection /></el-icon>
          </div>
          <h2>选择一个风格开始</h2>
          <p>您需要在上方选择或创建一个目标风格，才能开始文本转换</p>
          <el-button type="primary" size="large" @click="$router.push('/style-training')">
            <el-icon><Plus /></el-icon>
            创建新风格
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useStyleStore } from '@/stores/style'
import { useMessageStore } from '@/stores/message'
import {
  Magic,
  Collection,
  ChatDotRound,
  User,
  Document,
  EditPen,
  Position,
  Delete,
  Upload,
  CopyDocument,
  Clock,
  Plus
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'

const styleStore = useStyleStore()
const messageStore = useMessageStore()

const selectedStyleId = ref('')
const originalText = ref('')
const requirement = ref('')
const messagesContainer = ref(null)
const activeTab = ref('text')

const inputTabs = [
  { key: 'text', label: '原文', icon: Document },
  { key: 'requirement', label: '需求', icon: EditPen }
]

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

async function deleteMessage(messageId) {
  try {
    await ElMessageBox.confirm('确定要删除这条消息吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await messageStore.deleteMessage(selectedStyleId.value, messageId)
    ElMessage.success('消息已删除')
  } catch {
    // User cancelled
  }
}

function copyText(text) {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  })
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
.style-transfer-page {
  height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
}

/* Header */
.page-header {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 24px 28px;
  margin-bottom: 20px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 16px;
}

.title-icon {
  width: 56px;
  height: 56px;
  background: var(--primary-gradient);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: var(--shadow-glow);
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

.style-select {
  width: 320px;
}

.style-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
}

.style-info {
  display: flex;
  flex-direction: column;
}

.style-name {
  font-weight: 600;
  color: var(--text-primary);
}

.style-desc {
  font-size: 12px;
  color: var(--text-muted);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Main Container */
.main-container {
  flex: 1;
  min-height: 0;
}

.chat-layout {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Messages Container */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 0 4px;
}

.welcome-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.welcome-card {
  text-align: center;
  padding: 48px;
  background: var(--bg-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-color);
  max-width: 480px;
}

.welcome-icon {
  width: 120px;
  height: 120px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
  color: var(--primary-color);
}

.welcome-card h2 {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.welcome-card p {
  color: var(--text-secondary);
  margin: 0 0 32px;
}

.quick-tips {
  display: flex;
  justify-content: center;
  gap: 24px;
}

.tip-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 13px;
}

.tip-item .el-icon {
  width: 40px;
  height: 40px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Messages List */
.messages-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 8px 0;
}

.message-wrapper {
  display: flex;
  animation: fadeInUp 0.4s ease forwards;
  opacity: 0;
  transform: translateY(10px);
}

@keyframes fadeInUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-wrapper.user {
  justify-content: flex-end;
}

.message-bubble {
  max-width: 80%;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
  overflow: hidden;
}

.message-wrapper.user .message-bubble {
  background: var(--primary-gradient);
  border: none;
}

.message-wrapper.user .message-bubble :deep(*) {
  color: white !important;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.message-wrapper.user .message-header {
  border-bottom-color: rgba(255, 255, 255, 0.2);
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.message-avatar.assistant {
  background: var(--primary-gradient);
  color: white;
}

.message-role {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
}

.message-time {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-muted);
}

.message-status {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-muted);
  font-style: italic;
}

.message-body {
  padding: 16px;
}

.input-summary {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px dashed var(--border-color);
}

.message-wrapper.user .input-summary {
  border-bottom-color: rgba(255, 255, 255, 0.2);
}

.summary-item {
  margin-bottom: 8px;
}

.summary-item:last-child {
  margin-bottom: 0;
}

.summary-label {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.summary-text {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.summary-text.requirement {
  font-style: italic;
}

.response-content {
  font-size: 15px;
  line-height: 1.7;
  color: var(--text-primary);
  white-space: pre-wrap;
}

.message-actions {
  display: flex;
  gap: 8px;
  padding: 8px 16px;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
}

.message-wrapper.user .message-actions {
  background: rgba(255, 255, 255, 0.1);
  border-top-color: rgba(255, 255, 255, 0.2);
}

/* Typing Indicator */
.typing-indicator {
  display: flex;
  gap: 6px;
  padding: 12px 0;
}

.typing-indicator span {
  width: 10px;
  height: 10px;
  background: var(--primary-color);
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes typing {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

/* Input Panel */
.input-panel {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-color);
}

.input-container {
  padding: 20px;
}

.input-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.input-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
}

.input-tab:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.input-tab.active {
  background: var(--primary-gradient);
  color: white;
  box-shadow: var(--shadow-glow);
}

.input-fields {
  min-height: 180px;
}

.input-field {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.field-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.field-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--text-primary);
}

.field-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.char-count {
  font-size: 13px;
  color: var(--text-muted);
}

.custom-textarea :deep(.el-textarea__inner) {
  border-radius: var(--radius-md);
  border-color: var(--border-color);
  padding: 16px;
  font-size: 15px;
  line-height: 1.6;
  transition: all var(--transition-fast);
}

.custom-textarea :deep(.el-textarea__inner:focus) {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.input-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.send-button {
  padding: 12px 32px;
  font-weight: 600;
}

/* Empty State */
.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-card {
  text-align: center;
  padding: 64px;
  background: var(--bg-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-color);
  max-width: 520px;
}

.empty-illustration {
  margin-bottom: 24px;
}

.empty-card h2 {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.empty-card p {
  color: var(--text-secondary);
  margin: 0 0 24px;
}

/* Loading Animation */
.message-wrapper.loading .message-bubble {
  opacity: 0.8;
}
</style>
