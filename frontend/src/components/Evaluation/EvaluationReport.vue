<template>
  <div class="evaluation-report">
    <!-- Report Header -->
    <div class="report-header">
      <div class="header-left">
        <h2>{{ data?.task_name || '评估报告' }}</h2>
        <div class="task-tags">
          <el-tag size="small" type="success" effect="light">
            <el-icon><Check /></el-icon>
            已完成
          </el-tag>
          <el-tag size="small" type="info" effect="light">
            {{ data?.target_style || '-' }}
          </el-tag>
          <el-tag size="small" effect="light">
            {{ data?.generated_at }}
          </el-tag>
        </div>
      </div>
      <div class="header-actions">
        <el-button :icon="Refresh" circle @click="$emit('refresh')" />
      </div>
    </div>

    <!-- Overall Score Card -->
    <div class="overall-score-section">
      <div class="score-main-card">
        <div class="score-ring" :class="getScoreClass(data.overall_score)">
          <div class="score-value">{{ data.overall_score }}</div>
          <div class="score-label">综合评分</div>
        </div>
        <div class="score-info">
          <h3>评估概览</h3>
          <p>基于 {{ data.sample_count }} 组样本的自动评估结果</p>
          <div class="score-tags">
            <span class="score-tag" :class="getScoreClass(data.semantic_score)">
              语义保留 {{ data.semantic_score }}%
            </span>
            <span class="score-tag" :class="getScoreClass(data.style_score)">
              风格符合 {{ data.style_score }}%
            </span>
            <span class="score-tag" :class="getScoreClass(data.fluency_score)">
              文本流畅 {{ data.fluency_score }}%
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Metrics Grid -->
    <div class="metrics-section">
      <div class="section-title">
        <el-icon><PieChart /></el-icon>
        <span>详细指标</span>
      </div>
      <div class="metrics-grid">
        <div class="metric-item">
          <div class="metric-header">
            <span class="metric-name">语义保留率</span>
            <span class="metric-value" :class="getScoreClass(data.semantic_score)">
              {{ data.semantic_score }}%
            </span>
          </div>
          <div class="metric-bar">
            <div class="metric-fill" :class="getScoreClass(data.semantic_score)"
                 :style="{ width: data.semantic_score + '%' }"></div>
          </div>
          <p class="metric-desc">原文与转换后文本的语义相似度</p>
        </div>

        <div class="metric-item">
          <div class="metric-header">
            <span class="metric-name">风格符合度</span>
            <span class="metric-value" :class="getScoreClass(data.style_score)">
              {{ data.style_score }}%
            </span>
          </div>
          <div class="metric-bar">
            <div class="metric-fill" :class="getScoreClass(data.style_score)"
                 :style="{ width: data.style_score + '%' }"></div>
          </div>
          <p class="metric-desc">目标风格匹配程度</p>
        </div>

        <div class="metric-item">
          <div class="metric-header">
            <span class="metric-name">文本流畅度</span>
            <span class="metric-value" :class="getScoreClass(data.fluency_score)">
              {{ data.fluency_score }}%
            </span>
          </div>
          <div class="metric-bar">
            <div class="metric-fill" :class="getScoreClass(data.fluency_score)"
                 :style="{ width: data.fluency_score + '%' }"></div>
          </div>
          <p class="metric-desc">转换后文本的通顺程度</p>
        </div>

        <div class="metric-item">
          <div class="metric-header">
            <span class="metric-name">字符保留率</span>
            <span class="metric-value" :class="getScoreClass(data.char_retention)">
              {{ data.char_retention }}%
            </span>
          </div>
          <div class="metric-bar">
            <div class="metric-fill" :class="getScoreClass(data.char_retention)"
                 :style="{ width: data.char_retention + '%' }"></div>
          </div>
          <p class="metric-desc">原文字符在转换后的保留比例</p>
        </div>

        <div class="metric-item">
          <div class="metric-header">
            <span class="metric-name">词汇多样性</span>
            <span class="metric-value" :class="getScoreClass(data.vocab_diversity)">
              {{ data.vocab_diversity }}%
            </span>
          </div>
          <div class="metric-bar">
            <div class="metric-fill" :class="getScoreClass(data.vocab_diversity)"
                 :style="{ width: data.vocab_diversity + '%' }"></div>
          </div>
          <p class="metric-desc">唯一词占总词数的比例</p>
        </div>

        <div class="metric-item">
          <div class="metric-header">
            <span class="metric-name">长度变化率</span>
            <span class="metric-value">{{ data.length_ratio }}%</span>
          </div>
          <div class="metric-bar">
            <div class="metric-fill info" :style="{ width: Math.min(data.length_ratio, 100) + '%' }"></div>
          </div>
          <p class="metric-desc">转换后与原文长度比例</p>
        </div>
      </div>
    </div>

    <!-- User Comment Section -->
    <div class="comment-section">
      <div class="section-title">
        <el-icon><ChatDotRound /></el-icon>
        <span>用户评价</span>
      </div>

      <!-- View Mode: Show existing comment -->
      <div v-if="data.comment && !isEditing" class="comment-display">
        <div class="comment-content">
          <el-icon :size="18" color="#667eea"><ChatDotRound /></el-icon>
          <p class="comment-text">{{ data.comment }}</p>
        </div>
        <el-button
          type="primary"
          link
          :icon="Edit"
          @click="startEdit"
        >
          修改评价
        </el-button>
      </div>

      <!-- Edit Mode: Input form -->
      <div v-else class="comment-form">
        <el-input
          v-model="commentText"
          type="textarea"
          :rows="4"
          placeholder="请输入您对本次训练结果的评价（如：模型效果、改进建议等）"
          maxlength="2000"
          show-word-limit
          :disabled="submitting"
        />
        <div class="comment-actions">
          <el-button
            v-if="data.comment"
            @click="cancelEdit"
            :disabled="submitting"
          >
            取消
          </el-button>
          <el-button
            type="primary"
            :loading="submitting"
            :disabled="!commentText.trim()"
            @click="submitComment"
          >
            <el-icon><Check /></el-icon>
            {{ data.comment ? '保存修改' : '提交评价' }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- Sample Comparisons -->
    <div v-if="data.samples?.length" class="samples-section">
      <div class="section-title">
        <el-icon><Document /></el-icon>
        <span>样本对比</span>
      </div>
      <div class="sample-list">
        <div v-for="(sample, index) in data.samples" :key="index" class="sample-card">
          <div class="sample-header">
            <span class="sample-number">样本 {{ index + 1 }}</span>
          </div>
          <div class="sample-content">
            <div class="sample-box source">
              <div class="sample-label">
                <el-icon><Reading /></el-icon>
                原文
              </div>
              <div class="sample-text">{{ sample.source }}</div>
            </div>
            <div class="sample-arrow">
              <el-icon><Right /></el-icon>
            </div>
            <div class="sample-box target">
              <div class="sample-label">
                <el-icon><EditPen /></el-icon>
                转换后 ({{ data.target_style }})
              </div>
              <div class="sample-text">{{ sample.target }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Performance Info -->
    <div class="performance-section">
      <div class="performance-item">
        <el-icon><Timer /></el-icon>
        <span>平均响应时间: {{ data.avg_response_time }}s</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import {
  Check,
  Refresh,
  PieChart,
  Document,
  Reading,
  EditPen,
  Right,
  Timer,
  ChatDotRound,
  Edit
} from '@element-plus/icons-vue'
import { useTaskStore } from '@/stores/task'
import { ElMessage } from 'element-plus'

const taskStore = useTaskStore()

const props = defineProps({
  data: {
    type: Object,
    required: true,
    default: () => ({
      task_name: '',
      target_style: '',
      generated_at: '',
      overall_score: 0,
      sample_count: 0,
      semantic_score: 0,
      char_retention: 0,
      style_score: 0,
      fluency_score: 0,
      vocab_diversity: 0,
      length_ratio: 0,
      avg_response_time: 0,
      samples: [],
      comment: null
    })
  }
})

const emit = defineEmits(['refresh', 'commentSubmitted'])

// Comment state
const commentText = ref('')
const isEditing = ref(false)
const submitting = ref(false)

// Watch for data changes to sync comment text
watch(() => props.data.comment, (newComment) => {
  if (newComment && !isEditing.value) {
    commentText.value = newComment
  }
}, { immediate: true })

function startEdit() {
  commentText.value = props.data.comment || ''
  isEditing.value = true
}

function cancelEdit() {
  isEditing.value = false
  commentText.value = props.data.comment || ''
}

async function submitComment() {
  const trimmedComment = commentText.value.trim()
  if (!trimmedComment) {
    ElMessage.warning('请输入评价内容')
    return
  }

  submitting.value = true
  try {
    const taskId = props.data.task_id
    if (props.data.comment) {
      // Update existing comment
      await taskStore.updateComment(taskId, trimmedComment)
      ElMessage.success('评价已更新')
    } else {
      // Submit new comment
      await taskStore.submitComment(taskId, trimmedComment)
      ElMessage.success('评价已提交')
    }

    isEditing.value = false
    emit('commentSubmitted', { taskId, comment: trimmedComment })
  } catch (error) {
    ElMessage.error(props.data.comment ? '更新评价失败' : '提交评价失败')
    console.log(error)
  } finally {
    submitting.value = false
  }
}

function getScoreClass(score) {
  if (score >= 80) return 'excellent'
  if (score >= 60) return 'good'
  return 'poor'
}
</script>

<style scoped>
.evaluation-report {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
  overflow: hidden;
}

/* Report Header */
.report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px;
  border-bottom: 1px solid var(--border-color);
}

.header-left h2 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.task-tags {
  display: flex;
  gap: 8px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* Overall Score Section */
.overall-score-section {
  padding: 24px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%);
  border-bottom: 1px solid var(--border-color);
}

.score-main-card {
  display: flex;
  align-items: center;
  gap: 32px;
}

.score-ring {
  width: 140px;
  height: 140px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 6px solid;
  flex-shrink: 0;
}

.score-ring.excellent {
  border-color: #10b981;
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.score-ring.good {
  border-color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.score-ring.poor {
  border-color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.score-value {
  font-size: 42px;
  font-weight: 800;
  line-height: 1;
}

.score-label {
  font-size: 14px;
  margin-top: 4px;
  opacity: 0.8;
}

.score-info h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px;
}

.score-info p {
  color: var(--text-secondary);
  margin: 0 0 16px;
  font-size: 14px;
}

.score-tags {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.score-tag {
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}

.score-tag.excellent {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.score-tag.good {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.score-tag.poor {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

/* Metrics Section */
.metrics-section {
  padding: 24px;
  border-bottom: 1px solid var(--border-color);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 20px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.metric-item {
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.metric-name {
  font-size: 14px;
  color: var(--text-secondary);
}

.metric-value {
  font-size: 18px;
  font-weight: 700;
}

.metric-value.excellent {
  color: #10b981;
}

.metric-value.good {
  color: #f59e0b;
}

.metric-value.poor {
  color: #ef4444;
}

.metric-bar {
  height: 6px;
  background: var(--border-color);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 8px;
}

.metric-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.metric-fill.excellent {
  background: #10b981;
}

.metric-fill.good {
  background: #f59e0b;
}

.metric-fill.poor {
  background: #ef4444;
}

.metric-fill.info {
  background: var(--primary-color);
}

.metric-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

/* Samples Section */
.samples-section {
  padding: 24px;
  border-bottom: 1px solid var(--border-color);
}

.sample-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.sample-card {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.sample-header {
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.sample-number {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.sample-content {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
}

.sample-box {
  flex: 1;
  padding: 16px;
  border-radius: var(--radius-md);
}

.sample-box.source {
  background: var(--bg-secondary);
}

.sample-box.target {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%);
  border: 1px solid rgba(102, 126, 234, 0.1);
}

.sample-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sample-box.target .sample-label {
  color: var(--primary-color);
}

.sample-text {
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
}

.sample-arrow {
  color: var(--primary-color);
  font-size: 20px;
}

/* Performance Section */
.performance-section {
  padding: 16px 24px;
  background: var(--bg-secondary);
}

.performance-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

/* Comment Section */
.comment-section {
  padding: 24px;
  border-bottom: 1px solid var(--border-color);
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.02) 0%, rgba(139, 92, 246, 0.02) 100%);
}

.comment-display {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.comment-content {
  flex: 1;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.comment-text {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
}

.comment-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.comment-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.comment-actions .el-button--primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

/* Responsive */
@media (max-width: 1200px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .score-main-card {
    flex-direction: column;
    text-align: center;
  }

  .comment-display {
    flex-direction: column;
  }
}

@media (max-width: 992px) {
  .sample-content {
    flex-direction: column;
  }

  .sample-arrow {
    transform: rotate(90deg);
  }
}
</style>
