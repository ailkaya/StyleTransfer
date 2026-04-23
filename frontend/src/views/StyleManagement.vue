<template>
  <div class="style-management-page">
    <!-- Compact Header Bar with Filters -->
    <div class="management-bar">
      <div class="bar-left">
        <el-icon :size="18"><Collection /></el-icon>
        <span class="bar-label">风格管理</span>
        <el-tag size="small" type="info" effect="light">{{ styleStore.styles.length }} 个风格</el-tag>
      </div>

      <!-- Search Box -->
      <div class="bar-search">
        <div class="search-box" :class="{ focused: isSearchFocused }">
          <el-icon class="search-icon"><Search /></el-icon>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索风格名称..."
            @focus="isSearchFocused = true"
            @blur="isSearchFocused = false"
          />
          <el-icon v-if="searchQuery" class="clear-btn" @click="searchQuery = ''"><CircleClose /></el-icon>
        </div>
      </div>

      <!-- Status Filters -->
      <div class="bar-status-filters">
        <button
          :class="['status-btn', { active: statusFilter === '' }]"
          @click="statusFilter = ''"
        >
          全部
        </button>
        <button
          :class="['status-btn available', { active: statusFilter === 'COMPLETED' }]"
          @click="statusFilter = 'COMPLETED'"
        >
          <span class="status-dot"></span>
          可用
        </button>
        <button
          :class="['status-btn training', { active: statusFilter === 'PROCESSING' }]"
          @click="statusFilter = 'PROCESSING'"
        >
          <span class="status-dot"></span>
          训练中
        </button>
        <button
          :class="['status-btn evaluating', { active: statusFilter === 'EVALUATING' }]"
          @click="statusFilter = 'EVALUATING'"
        >
          <span class="status-dot"></span>
          评估中
        </button>
        <button
          :class="['status-btn preprocessing', { active: statusFilter === 'PREPROCESSING' }]"
          @click="statusFilter = 'PREPROCESSING'"
        >
          <span class="status-dot"></span>
          数据处理中
        </button>
      </div>

      <div class="bar-actions">
        <el-button v-if="searchQuery || statusFilter" link :icon="CircleClose" @click="clearFilters">
          清除筛选
        </el-button>
        <el-button type="primary" :icon="Plus" @click="$router.push('/style-training')">
          新建风格
        </el-button>
      </div>
    </div>

    <!-- Main Content -->
    <div class="management-content">
      <!-- List View -->
      <div v-if="filteredStyles.length > 0" v-loading="styleStore.loading" class="styles-list">
        <div class="list-header">
          <span>风格信息</span>
          <span>状态</span>
          <span>创建时间</span>
          <span>操作</span>
        </div>
        <StyleListItem
          v-for="(style, index) in filteredStyles"
          :key="style.id"
          :style="style"
          :animation-delay="index * 0.03"
          @click="viewStyleDetail"
          @edit="editStyle"
          @delete="confirmDelete"
          @viewProgress="openProgressDialog"
        />
      </div>

      <!-- Empty State -->
      <div v-if="!styleStore.loading && filteredStyles.length === 0" class="empty-state">
        <div class="empty-card">
          <div class="empty-icon">
            <el-icon :size="64"><Collection /></el-icon>
          </div>
          <h3>
            {{ searchQuery ? '没有找到匹配的风格' :
               statusFilter ? '没有符合筛选条件的风格' :
               '还没有创建任何风格' }}
          </h3>
          <p>
            {{ searchQuery || statusFilter ? '尝试调整搜索或筛选条件' :
               '创建您的第一个风格，开始AI风格转换之旅' }}
          </p>
          <div class="empty-actions">
            <el-button v-if="searchQuery || statusFilter" @click="clearFilters">
              <el-icon><CircleClose /></el-icon>
              清除筛选
            </el-button>
            <el-button v-else type="primary" @click="$router.push('/style-training')">
              <el-icon><Plus /></el-icon>
              创建第一个风格
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="filteredStyles.length > 0" class="pagination-wrapper">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[12, 24, 48]"
        :total="filteredTotal"
        layout="total, sizes, prev, pager, next"
        background
      />
    </div>

    <!-- Edit Dialog - Matching StyleTransfer Input Style -->
    <el-dialog
      v-model="editDialogVisible"
      title=""
      width="520px"
      :close-on-click-modal="false"
      class="edit-dialog"
      destroy-on-close
    >
      <div class="dialog-header-bar">
        <div class="dialog-icon">
          <el-icon :size="20"><Edit /></el-icon>
        </div>
        <span class="dialog-title">编辑风格</span>
      </div>

      <div class="dialog-body">
        <!-- Style Name Input -->
        <div class="input-group">
          <div class="input-header">
            <span class="input-label">
              <el-icon><Collection /></el-icon>
              风格名称
            </span>
          </div>
          <el-input
            v-model="editForm.name"
            placeholder="输入风格名称"
            maxlength="50"
            show-word-limit
          />
        </div>

        <!-- Target Style Input -->
        <div class="input-group">
          <div class="input-header">
            <span class="input-label">
              <el-icon><Star /></el-icon>
              目标风格
            </span>
          </div>
          <el-input
            v-model="editForm.target_style"
            placeholder="例如：正式、幽默、专业..."
          />
        </div>

        <!-- Description Input -->
        <div class="input-group">
          <div class="input-header">
            <span class="input-label">
              <el-icon><Document /></el-icon>
              风格描述
            </span>
          </div>
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="4"
            placeholder="描述这个风格的特点和适用场景..."
            maxlength="500"
            show-word-limit
            resize="none"
          />
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="saving"
            :disabled="!editForm.name.trim()"
            @click="saveEdit"
          >
            <el-icon v-if="!saving"><Check /></el-icon>
            <span>保存修改</span>
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- Training Progress Dialog -->
    <TrainingProgressDialog
      v-model:visible="progressDialogVisible"
      :style-id="selectedStyle?.id"
      :style-name="selectedStyle?.name"
      :style-status="selectedStyle?.status"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useStyleStore } from '@/stores/style'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Collection,
  Search,
  Edit,
  Check,
  CircleClose,
  Plus,
  Document,
  Star
} from '@element-plus/icons-vue'
import StyleListItem from '@/components/StyleManagement/StyleListItem.vue'
import TrainingProgressDialog from '@/components/StyleManagement/TrainingProgressDialog.vue'

const router = useRouter()
const route = useRoute()
const styleStore = useStyleStore()

const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(12)
const editDialogVisible = ref(false)
const saving = ref(false)
const isSearchFocused = ref(false)
const statusFilter = ref('') // '', 'COMPLETED', 'PROCESSING', 'EVALUATING', 'PREPROCESSING'

const editForm = reactive({
  id: '',
  name: '',
  description: '',
  target_style: ''
})

// Progress dialog state
const progressDialogVisible = ref(false)
const selectedStyle = ref(null)

const filteredTotal = computed(() => {
  let count = styleStore.styles.length
  if (statusFilter.value) {
    count = styleStore.styles.filter(s => s.task_status === statusFilter.value).length
  }
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    count = styleStore.styles.filter(s =>
      (statusFilter.value ? s.task_status === statusFilter.value : true) &&
      (s.name.toLowerCase().includes(query) ||
       (s.description && s.description.toLowerCase().includes(query)))
    ).length
  }
  return count
})

const filteredStyles = computed(() => {
  let styles = styleStore.styles

  // Status filter (using task_status instead of style.status)
  if (statusFilter.value) {
    styles = styles.filter(s => s.task_status === statusFilter.value)
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    styles = styles.filter(s =>
      s.name.toLowerCase().includes(query) ||
      (s.description && s.description.toLowerCase().includes(query))
    )
  }

  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return styles.slice(start, end)
})

function clearFilters() {
  statusFilter.value = ''
  searchQuery.value = ''
  currentPage.value = 1
}

// Polling for style updates every 5 seconds
let pollInterval = null

function startPolling() {
  // Fetch immediately
  styleStore.fetchStyles({ page_size: 100 })

  // Then poll every 5 seconds
  pollInterval = setInterval(() => {
    styleStore.fetchStyles({ page_size: 100 })
  }, 20000)
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

onMounted(() => {
  // Check for search query from route
  if (route.query.search) {
    searchQuery.value = route.query.search
  }
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})

function viewStyleDetail(style) {
  router.push({
    path: '/style-transfer',
    query: { styleId: style.id }
  })
}

function editStyle(style) {
  Object.assign(editForm, style)
  editDialogVisible.value = true
}

async function saveEdit() {
  saving.value = true
  try {
    await styleStore.updateStyle(editForm.id, {
      name: editForm.name,
      description: editForm.description,
      target_style: editForm.target_style
    })
    ElMessage.success('保存成功')
    editDialogVisible.value = false
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

async function confirmDelete(style) {
  try {
    await ElMessageBox.confirm(
      `确定要删除 "${style.name}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )
    await styleStore.deleteStyle(style.id)
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message)
    }
  }
}

function openProgressDialog(style) {
  selectedStyle.value = style
  progressDialogVisible.value = true
}
</script>

<style scoped>
.style-management-page {
  height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
}

/* Compact Header Bar - Matching StyleTransfer */
.management-bar {
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

.bar-search {
  flex: 1;
  max-width: 240px;
}

.bar-search .search-box {
  position: relative;
  width: 100%;
  background: var(--bg-secondary);
  border-radius: 10px;
  border: 1px solid var(--border-color);
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
}

.bar-search .search-box.focused {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.bar-search .search-icon {
  margin-left: 12px;
  color: var(--text-muted);
  font-size: 16px;
}

.bar-search input {
  flex: 1;
  padding: 9px 32px 9px 8px;
  border: none;
  background: transparent;
  font-size: 14px;
  color: var(--text-primary);
  outline: none;
}

.bar-search input::placeholder {
  color: var(--text-muted);
}

.bar-search .clear-btn {
  position: absolute;
  right: 8px;
  cursor: pointer;
  color: var(--text-muted);
  padding: 4px;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.bar-search .clear-btn:hover {
  background: var(--bg-card);
  color: var(--text-primary);
}

/* Status Filters in Bar */
.bar-status-filters {
  display: flex;
  gap: 6px;
}

.status-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.status-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.status-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
  color: white;
}

.status-btn.available.active {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.status-btn.training.active {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.status-btn.evaluating.active {
  background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);
}

.status-btn.preprocessing.active {
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
}

.status-btn.preprocessing .status-dot {
  background: #06b6d4;
}

.status-btn.evaluating .status-dot {
  background: #8b5cf6;
}

.status-btn .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.status-btn.available .status-dot {
  background: #10b981;
}

.status-btn.training .status-dot {
  background: #f59e0b;
}

/* Main Content */
.management-content {
  flex: 1;
  overflow-y: auto;
  padding: 0 4px;
}

/* List View */
.styles-list {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  overflow: hidden;
}

.list-header {
  display: grid;
  grid-template-columns: 1.5fr 85px 120px 210px;
  gap: 16px;
  padding: 12px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Empty State */
.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-card {
  text-align: center;
  padding: 48px;
  background: var(--bg-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-color);
  max-width: 400px;
}

.empty-icon {
  width: 100px;
  height: 100px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
  color: var(--primary-color);
}

.empty-card h3 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.empty-card p {
  color: var(--text-secondary);
  margin: 0 0 24px;
  font-size: 14px;
}

.empty-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}

/* Pagination */
.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 16px 0;
}

/* Edit Dialog - Matching StyleTransfer Input Panel */
:deep(.edit-dialog) {
  border-radius: var(--radius-lg);
  overflow: hidden;
}

:deep(.edit-dialog .el-dialog__header) {
  display: none;
}

:deep(.edit-dialog .el-dialog__body) {
  padding: 0;
}

:deep(.edit-dialog .el-dialog__footer) {
  padding: 16px 20px 20px;
  border-top: 1px solid var(--border-color);
}

.dialog-header-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.dialog-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.dialog-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.dialog-body {
  padding: 20px;
}

/* Input Groups - Matching StyleTransfer */
.input-group {
  margin-bottom: 16px;
}

.input-group:last-child {
  margin-bottom: 0;
}

.input-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.input-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.input-label .el-icon {
  color: #667eea;
}

.dialog-body :deep(.el-input__wrapper) {
  border-radius: 10px;
  box-shadow: 0 0 0 1px var(--border-color) inset;
  padding: 4px 12px;
  transition: all 0.3s ease;
}

.dialog-body :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #667eea inset;
}

.dialog-body :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px #667eea inset, 0 0 0 4px rgba(102, 126, 234, 0.1);
}

.dialog-body :deep(.el-input__inner) {
  height: 40px;
  font-size: 14px;
}

.dialog-body :deep(.el-textarea__inner) {
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 14px;
  line-height: 1.6;
  border: 1px solid var(--border-color);
  box-shadow: none;
  transition: all 0.3s ease;
}

.dialog-body :deep(.el-textarea__inner:hover) {
  border-color: #667eea;
}

.dialog-body :deep(.el-textarea__inner:focus) {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.dialog-body :deep(.el-input__count) {
  right: 10px;
  bottom: 8px;
  background: transparent;
  font-size: 12px;
  color: var(--text-muted);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.dialog-footer .el-button--primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.dialog-footer .el-button--primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.bar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* Responsive */
@media (max-width: 992px) {
  .management-bar {
    flex-wrap: wrap;
    gap: 12px;
  }

  .bar-search {
    order: 3;
    flex: 1 1 100%;
    max-width: none;
  }

  .bar-status-filters {
    order: 2;
  }
}

@media (max-width: 768px) {
  .management-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .bar-left,
  .bar-status-filters,
  .bar-actions {
    justify-content: space-between;
  }

  .bar-status-filters {
    flex-wrap: wrap;
  }

  .status-btn {
    flex: 1;
    min-width: 60px;
    justify-content: center;
  }

  .list-header {
    grid-template-columns: 1fr 210px;
  }

  .list-header span:nth-child(2),
  .list-header span:nth-child(3) {
    display: none;
  }
}
</style>
