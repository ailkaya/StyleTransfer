<template>
  <div class="style-transfer-page">
    <!-- Compact Style Selector Bar -->
    <div class="style-bar" v-if="styleStore.availableStyles.length > 0">
      <div class="style-selector-compact">
        <el-icon :size="18"><Collection /></el-icon>
        <span class="selector-label">当前风格:</span>
        <el-select
          v-model="selectedStyleId"
          placeholder="选择风格"
          size="default"
          class="style-select-mini"
          @change="onStyleChange"
        >
          <el-option
            v-for="style in styleStore.availableStyles"
            :key="style.id"
            :label="style.name"
            :value="style.id"
          >
            <div class="style-option">
              <span class="style-name">{{ style.name }}</span>
              <el-tag size="small" type="primary" effect="light">{{ style.target_style }}</el-tag>
            </div>
          </el-option>
        </el-select>
        <el-tag v-if="currentStyle" size="small" type="info" effect="light" class="target-tag">
          {{ currentStyle.target_style }}
        </el-tag>
      </div>
      <div class="style-actions">
        <el-button link :icon="Plus" @click="$router.push('/style-training')">新建</el-button>
        <el-button link :icon="Switch" @click="$router.push('/style-management')">切换</el-button>
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
                <el-icon :size="64"><ChatRound /></el-icon>
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
              <!-- User Message - Simplified -->
              <template v-if="msg.role === 'user'">
                <div class="message-bubble user-bubble">
                  <div class="user-content">
                    {{ msg.original_text + "\n<" + msg.requirement + ">" }}
                  </div>
                  <div class="message-meta">
                    <span class="message-time">{{ formatTime(msg.created_at) }}</span>
                    <el-button link size="small" :icon="Delete" @click="deleteMessage(msg.id)">删除</el-button>
                  </div>
                </div>
              </template>

              <!-- AI Message - Only response -->
              <template v-else>
                <div class="message-avatar assistant">
                  <el-icon :size="16"><Star /></el-icon>
                </div>
                <div class="message-bubble assistant-bubble">
                  <div class="assistant-header">
                    <span class="assistant-name">AI助手</span>
                    <span class="message-time">{{ formatTime(msg.created_at) }}</span>
                  </div>
                  <div class="assistant-content">
                    {{ msg.content }}
                  </div>
                  <div class="message-actions">
                    <el-button link size="small" :icon="CopyDocument" @click="copyText(msg.content)">复制</el-button>
                    <el-button link size="small" :icon="Delete" @click="deleteMessage(msg.id)">删除</el-button>
                  </div>
                </div>
              </template>
            </div>

            <!-- Loading State -->
            <div v-if="messageStore.sending" class="message-wrapper assistant loading">
              <div class="message-avatar assistant">
                <el-icon :size="16"><Star /></el-icon>
              </div>
              <div class="message-bubble assistant-bubble">
                <div class="assistant-header">
                  <span class="assistant-name">AI助手</span>
                  <span class="message-status">正在思考...</span>
                </div>
                <div class="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Input Area -->
        <div class="input-panel">
          <div class="input-container">
            <div class="input-row">
              <!-- Original Text Input -->
              <div class="input-column">
                <div class="field-header">
                  <span class="field-label">
                    <el-icon><Document /></el-icon>
                    原文
                  </span>
                  <div class="field-actions">
                    <el-upload
                      action=""
                      :auto-upload="false"
                      :show-file-list="false"
                      :on-change="handleFileChange"
                      accept=".txt,.md,.docx"
                    >
                      <el-button link type="primary" size="small" :icon="Upload">
                        上传
                      </el-button>
                    </el-upload>
                    <span class="char-count">{{ originalText.length }}</span>
                  </div>
                </div>
                <el-input
                  v-model="originalText"
                  type="textarea"
                  :rows="3"
                  placeholder="输入原文..."
                  resize="none"
                  class="custom-textarea"
                />
              </div>

              <!-- Requirement Input -->
              <div class="input-column">
                <div class="field-header">
                  <span class="field-label">
                    <el-icon><EditPen /></el-icon>
                    需求
                  </span>
                  <span class="char-count">{{ requirement.length }}</span>
                </div>
                <el-input
                  v-model="requirement"
                  type="textarea"
                  :rows="3"
                  placeholder="输入转换需求..."
                  resize="none"
                  class="custom-textarea"
                />
              </div>
            </div>

            <div class="input-footer">
              <el-button
                link
                size="small"
                :icon="Delete"
                @click="clearHistory"
              >
                清空
              </el-button>
              <el-button
                type="primary"
                :icon="Position"
                :loading="messageStore.sending"
                :disabled="!canSend"
                class="send-button"
                @click="sendMessage"
              >
                发送
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
          <p>您需要选择或创建一个目标风格，才能开始文本转换</p>
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
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStyleStore } from '@/stores/style'
import { useMessageStore } from '@/stores/message'
import {
  Star,
  Collection,
  ChatRound,
  User,
  Document,
  EditPen,
  Position,
  Delete,
  Upload,
  CopyDocument,
  Clock,
  Plus,
  Switch
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const styleStore = useStyleStore()
const messageStore = useMessageStore()

const selectedStyleId = ref('')

// Handle URL query params for auto-selecting style
onMounted(() => {
  const styleIdFromQuery = route.query.styleId
  if (styleIdFromQuery && styleStore.availableStyles.length > 0) {
    // Check if the style exists and is available
    const styleExists = styleStore.availableStyles.find(s => s.id === styleIdFromQuery)
    if (styleExists) {
      selectedStyleId.value = styleIdFromQuery
      onStyleChange()
      // Clear the query param from URL without reloading
      router.replace({ path: '/style-transfer', query: {} })
    }
  }
})

// Also watch for when styles are loaded (in case they load after component mounts)
watch(() => styleStore.availableStyles.length, (newLength) => {
  if (newLength > 0 && route.query.styleId && !selectedStyleId.value) {
    const styleIdFromQuery = route.query.styleId
    const styleExists = styleStore.availableStyles.find(s => s.id === styleIdFromQuery)
    if (styleExists) {
      selectedStyleId.value = styleIdFromQuery
      onStyleChange()
      router.replace({ path: '/style-transfer', query: {} })
    }
  }
})
const originalText = ref('')
const requirement = ref('')
const messagesContainer = ref(null)

const currentStyle = computed(() =>
  styleStore.getStyleById(selectedStyleId.value)
)

const canSend = computed(() =>
  selectedStyleId.value &&
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

/* Compact Style Bar */
.style-bar {
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

.style-selector-compact {
  display: flex;
  align-items: center;
  gap: 10px;
}

.selector-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.style-select-mini {
  width: 200px;
}

.style-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
}

.style-option .style-name {
  font-weight: 500;
  color: var(--text-primary);
}

.target-tag {
  margin-left: 8px;
}

.style-actions {
  display: flex;
  gap: 8px;
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
  gap: 12px;
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

/* Messages - New Simplified Style */
.messages-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 8px 0;
  overflow-x: hidden;
  max-width: 100%;
  box-sizing: border-box;
}

.message-wrapper {
  display: flex;
  animation: fadeInUp 0.4s ease forwards;
  opacity: 0;
  transform: translateY(10px);
}

.message-wrapper.user {
  justify-content: flex-end;
}

.message-wrapper.assistant {
  align-items: flex-start;
  gap: 12px;
  justify-content: flex-start;
}

@keyframes fadeInUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* User Message Bubble - Modern Style */
.user-bubble {
  min-width: 80px;
  max-width: 85%;
  width: fit-content;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 20px 20px 4px 20px;
  padding: 14px 18px;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
  position: relative;
}

.user-bubble::after {
  content: '';
  position: absolute;
  bottom: 0;
  right: -6px;
  width: 12px;
  height: 12px;
  background: linear-gradient(135deg, #764ba2 0%, #764ba2 100%);
  clip-path: polygon(0 0, 0% 100%, 100% 100%);
}

.user-content {
  font-size: 15px;
  line-height: 1.7;
  word-break: break-word;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  width: fit-content;
}

.message-meta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.15);
}

.message-meta .message-time {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.8);
  font-weight: 500;
}

.message-meta .el-button {
  color: rgba(255, 255, 255, 0.9);
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.message-meta .el-button:hover {
  color: white;
  background: rgba(255, 255, 255, 0.15);
}

/* Assistant Message - Modern Style */
.message-avatar.assistant {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  border: 2px solid white;
}

.assistant-bubble {
  min-width: 120px;
  max-width: 85%;
  width: fit-content;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border-radius: 8px 20px 20px 20px;
  border: 1px solid rgba(102, 126, 234, 0.15);
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  position: relative;
}

.assistant-bubble::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
}

.assistant-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: rgba(102, 126, 234, 0.04);
  border-bottom: 1px solid rgba(102, 126, 234, 0.08);
}

.assistant-name {
  font-size: 13px;
  font-weight: 700;
  color: #667eea;
  display: flex;
  align-items: center;
  gap: 6px;
}

.assistant-name::before {
  content: '';
  width: 6px;
  height: 6px;
  background: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 8px #10b981;
}

.assistant-header .message-time {
  font-size: 11px;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.6);
  padding: 2px 8px;
  border-radius: 10px;
}

.assistant-content {
  padding: 16px 18px;
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
  width: fit-content;
  min-width: 100%;
  box-sizing: border-box;
}

.message-actions {
  display: flex;
  gap: 12px;
  padding: 10px 16px;
  background: rgba(102, 126, 234, 0.03);
  border-top: 1px solid rgba(102, 126, 234, 0.08);
  width: fit-content;
  min-width: 100%;
  box-sizing: border-box;
}

.message-actions .el-button {
  font-size: 12px;
  color: var(--text-secondary);
  transition: all 0.2s ease;
}

.message-actions .el-button:hover {
  color: #667eea;
  transform: translateY(-1px);
}

/* Loading State */
.message-wrapper.loading {
  opacity: 0.8;
}

.message-wrapper.loading .assistant-bubble {
  min-width: 200px;
}

.message-status {
  font-size: 11px;
  color: var(--text-muted);
  font-style: italic;
}

/* Typing Indicator */
.typing-indicator {
  display: flex;
  gap: 6px;
  padding: 14px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
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
  padding: 16px;
}

.input-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}

.input-column {
  display: flex;
  flex-direction: column;
}

.field-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.field-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.field-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.char-count {
  font-size: 12px;
  color: var(--text-muted);
}

.custom-textarea :deep(.el-textarea__inner) {
  border-radius: var(--radius-md);
  border-color: var(--border-color);
  padding: 12px;
  font-size: 14px;
  line-height: 1.5;
  transition: all var(--transition-fast);
}

.custom-textarea :deep(.el-textarea__inner:focus) {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.task-type-selector {
  display: flex;
  align-items: center;
  flex: 1;
}

.task-type-selector :deep(.el-radio-group) {
  width: 100%;
  display: flex;
}

.task-type-selector :deep(.el-radio-button) {
  flex: 1;
}

.task-type-selector :deep(.el-radio-button__inner) {
  width: 100%;
}

.input-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.send-button {
  padding: 10px 24px;
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

/* Responsive */
@media (max-width: 768px) {
  .style-bar {
    flex-direction: column;
    gap: 12px;
  }

  .style-selector-compact {
    width: 100%;
  }

  .style-select-mini {
    flex: 1;
  }

  .style-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .input-row {
    grid-template-columns: 1fr;
  }

  .user-bubble {
    max-width: 85%;
  }

  .assistant-bubble {
    max-width: 85%;
  }
}
</style>
