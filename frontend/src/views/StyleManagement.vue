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
          :class="['status-btn available', { active: statusFilter === 'available' }]"
          @click="statusFilter = 'available'"
        >
          <span class="status-dot"></span>
          可用
        </button>
        <button
          :class="['status-btn training', { active: statusFilter === 'training' }]"
          @click="statusFilter = 'training'"
        >
          <span class="status-dot"></span>
          训练中
        </button>
        <button
          :class="['status-btn evaluating', { active: statusFilter === 'evaluating' }]"
          @click="statusFilter = 'evaluating'"
        >
          <span class="status-dot"></span>
          评估中
        </button>
      </div>

      <div class="bar-actions">
        <!-- View Toggle -->
        <div class="view-toggle">
          <button
            :class="['toggle-btn', { active: viewMode === 'grid' }]"
            @click="viewMode = 'grid'"
          >
            <el-icon><Grid /></el-icon>
          </button>
          <button
            :class="['toggle-btn', { active: viewMode === 'list' }]"
            @click="viewMode = 'list'"
          >
            <el-icon><List /></el-icon>
          </button>
        </div>
        <el-button type="primary" :icon="Plus" @click="$router.push('/style-training')">
          新建风格
        </el-button>
      </div>
    </div>

    <!-- Main Content -->
    <div class="management-content">
      <!-- Grid View -->
      <div v-if="viewMode === 'grid' && filteredStyles.length > 0" v-loading="styleStore.loading" class="styles-grid">
        <div
          v-for="(style, index) in filteredStyles"
          :key="style.id"
          class="style-card"
          :class="[getStatusClass(style.status), { 'new-card': index < 3 }]"
          :style="{ animationDelay: `${index * 0.05}s` }"
        >
          <div class="card-header">
            <div class="header-status" :class="style.status">
              <span class="status-indicator"></span>
              <span class="status-text">{{ getStatusLabel(style.status) }}</span>
            </div>
            <div class="header-actions">
              <el-button
                link
                :icon="Edit"
                :disabled="style.status === 'training' || style.status === 'evaluating'"
                @click="editStyle(style)"
              />
              <el-button
                link
                type="danger"
                :icon="Delete"
                :disabled="style.status === 'training' || style.status === 'evaluating'"
                @click="confirmDelete(style)"
              />
            </div>
          </div>

          <div class="card-body" @click="viewStyleDetail(style)">
            <div class="style-icon" :class="style.status">
              <el-icon :size="28"><Collection /></el-icon>
            </div>
            <h3 class="style-name">{{ style.name }}</h3>
            <p class="style-target">{{ style.target_style }}</p>
            <p class="style-description">{{ style.description || '暂无描述' }}</p>
          </div>

          <div class="card-footer">
            <span class="footer-meta">
              <el-icon><Calendar /></el-icon>
              {{ formatTime(style.created_at) }}
            </span>
            <el-button
              v-if="isStyleAvailable(style.status)"
              type="primary"
              size="small"
              @click="viewStyleDetail(style)"
            >
              使用
            </el-button>
            <el-button
              v-else
              type="primary"
              size="small"
              disabled
            >
              {{ getStatusLabel(style.status) }}
            </el-button>
          </div>
        </div>
      </div>

      <!-- List View -->
      <div v-else-if="viewMode === 'list' && filteredStyles.length > 0" v-loading="styleStore.loading" class="styles-list">
        <div class="list-header">
          <span>风格信息</span>
          <span>状态</span>
          <span>创建时间</span>
          <span>操作</span>
        </div>
        <div
          v-for="(style, index) in filteredStyles"
          :key="style.id"
          class="list-row"
          :class="getStatusClass(style.status)"
          :style="{ animationDelay: `${index * 0.03}s` }"
        >
          <div class="list-info" @click="viewStyleDetail(style)">
            <div class="list-icon" :class="style.status">
              <el-icon><Collection /></el-icon>
            </div>
            <div class="list-text">
              <span class="list-name">{{ style.name }}</span>
              <span class="list-target">{{ style.target_style }}</span>
            </div>
          </div>

          <div class="list-status" :class="style.status">
            <span class="status-indicator"></span>
            <span>{{ getStatusLabel(style.status) }}</span>
          </div>

          <div class="list-date">
            {{ formatTime(style.created_at) }}
          </div>

          <div class="list-actions">
            <el-button
              link
              type="primary"
              :icon="Edit"
              :disabled="style.status === 'training' || style.status === 'evaluating'"
              @click="editStyle(style)"
            >
              编辑
            </el-button>
            <el-button
              link
              type="danger"
              :icon="Delete"
              :disabled="style.status === 'training' || style.status === 'evaluating'"
              @click="confirmDelete(style)"
            >
              删除
            </el-button>
          </div>
        </div>
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useStyleStore } from '@/stores/style'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Collection,
  Search,
  Edit,
  Delete,
  Check,
  Calendar,
  Grid,
  List,
  CircleClose,
  Plus,
  Document,
  Star
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const router = useRouter()
const styleStore = useStyleStore()

const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(12)
const viewMode = ref('grid')
const editDialogVisible = ref(false)
const saving = ref(false)
const isSearchFocused = ref(false)
const statusFilter = ref('') // '', 'available', 'training'

const editForm = reactive({
  id: '',
  name: '',
  description: '',
  target_style: ''
})

const filteredTotal = computed(() => {
  let count = styleStore.styles.length
  if (statusFilter.value) {
    count = styleStore.styles.filter(s => s.status === statusFilter.value).length
  }
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    count = styleStore.styles.filter(s =>
      (statusFilter.value ? s.status === statusFilter.value : true) &&
      (s.name.toLowerCase().includes(query) ||
       (s.description && s.description.toLowerCase().includes(query)))
    ).length
  }
  return count
})

const filteredStyles = computed(() => {
  let styles = styleStore.styles

  // Status filter
  if (statusFilter.value) {
    styles = styles.filter(s => s.status === statusFilter.value)
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

onMounted(() => {
  styleStore.fetchStyles({ page_size: 100 })
})

function getStatusClass(status) {
  const classes = {
    'pending': 'status-pending',
    'training': 'status-training',
    'completed': 'status-completed',
    'failed': 'status-failed',
    'available': 'status-available',
    'evaluating': 'status-evaluating'
  }
  return classes[status] || 'status-pending'
}

function getStatusLabel(status) {
  const labels = {
    'pending': '待训练',
    'training': '训练中',
    'completed': '已完成',
    'failed': '失败',
    'available': '可用',
    'evaluating': '评估中'
  }
  return labels[status] || status
}

function isStyleAvailable(status) {
  return status === 'available'
}

function formatTime(time) {
  return dayjs(time).format('YYYY-MM-DD HH:mm')
}

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

/* View Toggle */
.view-toggle {
  display: flex;
  gap: 4px;
  background: var(--bg-secondary);
  padding: 4px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toggle-btn:hover {
  color: var(--text-primary);
  background: var(--bg-card);
}

.toggle-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

/* Main Content */
.management-content {
  flex: 1;
  overflow-y: auto;
  padding: 0 4px;
}

/* Grid View */
.styles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.style-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  overflow: hidden;
  transition: all 0.3s ease;
  animation: fadeInUp 0.4s ease forwards;
  opacity: 0;
  transform: translateY(10px);
  display: flex;
  flex-direction: column;
}

@keyframes fadeInUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.style-card:hover {
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
  border-color: rgba(102, 126, 234, 0.3);
}

.style-card.status-available {
  border-color: rgba(16, 185, 129, 0.3);
}

.style-card.status-available:hover {
  border-color: #10b981;
}

.style-card.status-training {
  border-color: rgba(245, 158, 11, 0.3);
}

.style-card.status-evaluating {
  border-color: rgba(139, 92, 246, 0.3);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.header-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
}

.header-status .status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.header-status.available {
  color: #059669;
}

.header-status.available .status-indicator {
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
}

.header-status.training {
  color: #d97706;
}

.header-status.training .status-indicator {
  background: #f59e0b;
  box-shadow: 0 0 8px #f59e0b;
}

.header-status.evaluating {
  color: #7c3aed;
}

.header-status.evaluating .status-indicator {
  background: #8b5cf6;
  box-shadow: 0 0 8px #8b5cf6;
}

.header-status.pending {
  color: #64748b;
}

.header-status.pending .status-indicator {
  background: #94a3b8;
}

.header-actions {
  display: flex;
  gap: 4px;
}

.card-body {
  flex: 1;
  padding: 20px 16px;
  text-align: center;
  cursor: pointer;
}

.style-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  font-size: 28px;
  color: white;
  transition: all 0.3s ease;
}

.style-icon.available {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  box-shadow: 0 8px 20px rgba(16, 185, 129, 0.3);
}

.style-icon.training {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  box-shadow: 0 8px 20px rgba(245, 158, 11, 0.3);
}

.style-icon.pending {
  background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%);
  box-shadow: 0 8px 20px rgba(148, 163, 184, 0.3);
}

.style-icon.evaluating {
  background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);
  box-shadow: 0 8px 20px rgba(139, 92, 246, 0.3);
}

.style-card:hover .style-icon {
  transform: scale(1.05);
}

.style-name {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.style-target {
  font-size: 13px;
  color: #667eea;
  font-weight: 600;
  margin: 0 0 10px;
}

.style-description {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.5;
  height: 40px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
}

.footer-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
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
  grid-template-columns: 2fr 100px 140px 140px;
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

.list-row {
  display: grid;
  grid-template-columns: 2fr 100px 140px 140px;
  gap: 16px;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  transition: all 0.2s ease;
  animation: slideIn 0.3s ease forwards;
  opacity: 0;
  transform: translateX(-10px);
}

@keyframes slideIn {
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.list-row:last-child {
  border-bottom: none;
}

.list-row:hover {
  background: rgba(102, 126, 234, 0.03);
}

.list-info {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.list-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 18px;
  flex-shrink: 0;
}

.list-icon.available {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.list-icon.training {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.list-icon.pending {
  background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%);
}

.list-icon.evaluating {
  background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);
}

.list-text {
  min-width: 0;
}

.list-name {
  display: block;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.list-target {
  font-size: 12px;
  color: #667eea;
  font-weight: 500;
}

.list-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
}

.list-status.available {
  color: #059669;
}

.list-status.training {
  color: #d97706;
}

.list-status.pending {
  color: #64748b;
}

.list-status.evaluating {
  color: #7c3aed;
}

.list-status.evaluating .status-indicator {
  background: #8b5cf6;
  box-shadow: 0 0 6px #8b5cf6;
}

.list-status .status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.list-status.available .status-indicator {
  background: #10b981;
  box-shadow: 0 0 6px #10b981;
}

.list-status.training .status-indicator {
  background: #f59e0b;
  box-shadow: 0 0 6px #f59e0b;
}

.list-date {
  font-size: 13px;
  color: var(--text-muted);
}

.list-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
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

  .styles-grid {
    grid-template-columns: 1fr;
  }

  .list-header,
  .list-row {
    grid-template-columns: 1fr auto;
  }

  .list-header span:nth-child(2),
  .list-header span:nth-child(3),
  .list-status,
  .list-date {
    display: none;
  }
}
</style>
