<template>
  <div class="management-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-title">
          <div class="title-icon">
            <el-icon :size="28"><Collection /></el-icon>
          </div>
          <div class="title-text">
            <h1>风格管理</h1>
            <p>查看和管理您的所有风格</p>
          </div>
        </div>
        <div class="header-stats">
          <div class="stat-box">
            <span class="stat-value">{{ styleStore.styles.length }}</span>
            <span class="stat-label">总风格数</span>
          </div>
          <div class="stat-box available">
            <span class="stat-value">{{ availableCount }}</span>
            <span class="stat-label">可用</span>
          </div>
          <div class="stat-box training">
            <span class="stat-value">{{ trainingCount }}</span>
            <span class="stat-label">训练中</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <div class="search-box">
        <el-icon><Search /></el-icon>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索风格名称..."
        />
        <el-icon v-if="searchQuery" class="clear-btn" @click="searchQuery = ''"><CircleClose /></el-icon>
      </div>
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
    </div>

    <!-- Grid View -->
    <div v-if="viewMode === 'grid'" v-loading="styleStore.loading" class="styles-grid">
      <div
        v-for="style in filteredStyles"
        :key="style.id"
        class="style-card"
        @click="viewStyleDetail(style)"
      >
        <div class="card-header-gradient" :class="getStatusClass(style.status)">
          <div class="card-status-badge">
            <el-icon v-if="style.status === 'available'" :size="14"><Check /></el-icon>
            <el-icon v-else-if="style.status === 'training'" :size="14"><Loading /></el-icon>
            <el-icon v-else :size="14"><Clock /></el-icon>
            {{ getStatusLabel(style.status) }}
          </div>
        </div>

        <div class="card-body">
          <h3 class="style-name">{{ style.name }}</h3>
          <p class="style-description">{{ style.description || '暂无描述' }}</p>

          <div class="style-target">
            <el-tag size="small" effect="light" :type="getTagType(style.status)">
              {{ style.target_style }}
            </el-tag>
            <span class="base-model">{{ style.base_model }}</span>
          </div>

          <div class="style-meta">
            <div class="meta-item">
              <el-icon><Calendar /></el-icon>
              <span>{{ formatTime(style.created_at) }}</span>
            </div>
          </div>
        </div>

        <div class="card-actions">
          <el-button
            link
            type="primary"
            :icon="Edit"
            :disabled="style.status === 'training'"
            @click.stop="editStyle(style)"
          >
            编辑
          </el-button>
          <el-button
            link
            type="danger"
            :icon="Delete"
            :disabled="style.status === 'training'"
            @click.stop="confirmDelete(style)"
          >
            删除
          </el-button>
        </div>
      </div>
    </div>

    <!-- List View -->
    <div v-else v-loading="styleStore.loading" class="styles-list">
      <div class="list-header">
        <span class="col-name">风格名称</span>
        <span class="col-target">目标风格</span>
        <span class="col-status">状态</span>
        <span class="col-date">创建时间</span>
        <span class="col-actions">操作</span>
      </div>
      <div
        v-for="style in filteredStyles"
        :key="style.id"
        class="list-item"
      >
        <div class="col-name">
          <div class="name-main">{{ style.name }}</div>
          <div class="name-desc">{{ style.description || '暂无描述' }}</div>
        </div>
        <div class="col-target">
          <el-tag size="small" :type="getTagType(style.status)">
            {{ style.target_style }}
          </el-tag>
        </div>
        <div class="col-status">
          <div class="status-indicator" :class="style.status">
            <span class="status-dot" />
            {{ getStatusLabel(style.status) }}
          </div>
        </div>
        <div class="col-date">{{ formatTime(style.created_at) }}</div>
        <div class="col-actions">
          <el-button
            link
            type="primary"
            :icon="Edit"
            :disabled="style.status === 'training'"
            @click="editStyle(style)"
          >
            编辑
          </el-button>
          <el-button
            link
            type="danger"
            :icon="Delete"
            :disabled="style.status === 'training'"
            @click="confirmDelete(style)"
          >
            删除
          </el-button>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="!styleStore.loading && filteredStyles.length === 0" class="empty-state">
      <div class="empty-content">
        <el-icon :size="64" color="#cbd5e1"><Collection /></el-icon>
        <h3>{{ searchQuery ? '没有找到匹配的风格' : '还没有创建任何风格' }}</h3>
        <p>{{ searchQuery ? '尝试其他搜索词' : '创建您的第一个风格开始训练' }}</p>
        <el-button v-if="!searchQuery" type="primary" @click="$router.push('/style-training')">
          <el-icon><Plus /></el-icon>
          创建风格
        </el-button>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="filteredStyles.length > 0" class="pagination-wrapper">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[12, 24, 48]"
        :total="styleStore.styles.length"
        layout="total, sizes, prev, pager, next"
        background
      />
    </div>

    <!-- Edit Dialog -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑风格"
      width="500px"
      :close-on-click-modal="false"
      class="modern-dialog"
    >
      <el-form :model="editForm" label-position="top">
        <el-form-item label="风格名称">
          <el-input v-model="editForm.name" size="large" />
        </el-form-item>

        <el-form-item label="风格描述">
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="3"
          />
        </el-form-item>

        <el-form-item label="目标风格">
          <el-input v-model="editForm.target_style" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">
          保存修改
        </el-button>
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
  Loading,
  Clock,
  Calendar,
  Grid,
  List,
  CircleClose,
  Plus
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const styleStore = useStyleStore()

const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(12)
const viewMode = ref('grid')
const editDialogVisible = ref(false)
const saving = ref(false)

const editForm = reactive({
  id: '',
  name: '',
  description: '',
  target_style: ''
})

const availableCount = computed(() =>
  styleStore.styles.filter(s => s.status === 'available').length
)

const trainingCount = computed(() =>
  styleStore.styles.filter(s => s.status === 'training').length
)

const filteredStyles = computed(() => {
  let styles = styleStore.styles

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    styles = styles.filter(s =>
      s.name.toLowerCase().includes(query) ||
      (s.description && s.description.toLowerCase().includes(query))
    )
  }

  // Pagination
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return styles.slice(start, end)
})

onMounted(() => {
  styleStore.fetchStyles({ page_size: 100 })
})

function getStatusClass(status) {
  const classes = {
    'pending': 'status-pending',
    'training': 'status-training',
    'completed': 'status-completed',
    'failed': 'status-failed',
    'available': 'status-available'
  }
  return classes[status] || 'status-pending'
}

function getStatusLabel(status) {
  const labels = {
    'pending': '待训练',
    'training': '训练中',
    'completed': '已完成',
    'failed': '失败',
    'available': '可用'
  }
  return labels[status] || status
}

function getTagType(status) {
  const types = {
    'pending': 'info',
    'training': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'available': 'success'
  }
  return types[status] || 'info'
}

function formatTime(time) {
  return dayjs(time).format('YYYY-MM-DD HH:mm')
}

function viewStyleDetail(style) {
  // Navigate to style transfer with this style selected
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
.management-page {
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
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.3);
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

.header-stats {
  display: flex;
  gap: 16px;
}

.stat-box {
  text-align: center;
  padding: 12px 24px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  min-width: 80px;
}

.stat-box.available {
  background: rgba(16, 185, 129, 0.1);
}

.stat-box.training {
  background: rgba(245, 158, 11, 0.1);
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-box.available .stat-value {
  color: var(--success-color);
}

.stat-box.training .stat-value {
  color: var(--warning-color);
}

.stat-label {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

/* Toolbar */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.search-box {
  position: relative;
  width: 320px;
}

.search-box .el-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
}

.search-box input {
  width: 100%;
  padding: 12px 40px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  font-size: 14px;
  transition: all var(--transition-fast);
}

.search-box input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.search-box .clear-btn {
  right: 14px;
  left: auto;
  cursor: pointer;
  color: var(--text-muted);
}

.view-toggle {
  display: flex;
  gap: 4px;
  background: var(--bg-card);
  padding: 4px;
  border-radius: var(--radius-md);
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
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.toggle-btn:hover {
  color: var(--text-primary);
  background: var(--bg-secondary);
}

.toggle-btn.active {
  background: var(--primary-gradient);
  color: white;
}

/* Grid View */
.styles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.style-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
  overflow: hidden;
  cursor: pointer;
  transition: all var(--transition-normal);
}

.style-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-color: var(--primary-color);
}

.card-header-gradient {
  height: 80px;
  position: relative;
  padding: 16px;
}

.status-pending { background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%); }
.status-training { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
.status-completed { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
.status-failed { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); }
.status-available { background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); }

.card-status-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(8px);
  border-radius: 20px;
  color: white;
  font-size: 12px;
  font-weight: 600;
}

.card-body {
  padding: 20px;
}

.style-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.style-description {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0 0 16px;
  line-height: 1.5;
  height: 42px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.style-target {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.base-model {
  font-size: 12px;
  color: var(--text-muted);
}

.style-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-muted);
}

.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
}

/* List View */
.styles-list {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
  overflow: hidden;
  margin-bottom: 24px;
}

.list-header {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr 140px;
  gap: 16px;
  padding: 16px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.list-item {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr 140px;
  gap: 16px;
  padding: 20px;
  border-bottom: 1px solid var(--border-color);
  transition: background var(--transition-fast);
}

.list-item:hover {
  background: var(--bg-secondary);
}

.list-item:last-child {
  border-bottom: none;
}

.col-name .name-main {
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.col-name .name-desc {
  font-size: 13px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-indicator.pending .status-dot { background: #94a3b8; }
.status-indicator.training .status-dot { background: #f59e0b; box-shadow: 0 0 8px #f59e0b; }
.status-indicator.available .status-dot { background: #10b981; }
.status-indicator.failed .status-dot { background: #ef4444; }

.status-indicator.pending { color: #64748b; }
.status-indicator.training { color: #d97706; }
.status-indicator.available { color: #059669; }
.status-indicator.failed { color: #dc2626; }

.col-actions {
  display: flex;
  gap: 8px;
}

/* Empty State */
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
}

.empty-content {
  text-align: center;
}

.empty-content h3 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 20px 0 8px;
}

.empty-content p {
  color: var(--text-secondary);
  margin: 0 0 24px;
}

/* Pagination */
.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding-top: 20px;
}

/* Responsive */
@media (max-width: 1024px) {
  .styles-grid {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  }

  .list-header,
  .list-item {
    grid-template-columns: 2fr 1fr 100px;
  }

  .col-target,
  .col-date {
    display: none;
  }
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    gap: 20px;
  }

  .header-stats {
    width: 100%;
    justify-content: space-between;
  }

  .search-box {
    width: 100%;
  }
}

/* Dialog */
:deep(.modern-dialog .el-dialog__header) {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
  margin-right: 0;
}

:deep(.modern-dialog .el-dialog__body) {
  padding: 24px;
}

:deep(.modern-dialog .el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
}
</style>
