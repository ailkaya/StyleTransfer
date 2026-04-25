<template>
  <div class="explore-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-title">
          <div class="title-icon">
            <el-icon :size="28"><Compass /></el-icon>
          </div>
          <div class="title-text">
            <h1>探索</h1>
            <p>发现社区共享的风格模型与训练数据</p>
          </div>
        </div>
        <div class="header-actions">
          <template v-if="exploreStore.isLoggedIn">
            <el-tag type="success" effect="light">
              <el-icon><User /></el-icon>
              {{ exploreStore.displayName }}
            </el-tag>
            <el-button @click="exploreStore.logout()">退出</el-button>
          </template>
          <template v-else>
            <el-button @click="showAuthDialog = true">登录 / 注册</el-button>
          </template>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <el-tabs v-model="activeTab" class="explore-tabs">
      <el-tab-pane label="Adapter" name="adapters">
        <template #label>
          <span class="tab-label"><el-icon><Cpu /></el-icon> Adapter</span>
        </template>
      </el-tab-pane>
      <el-tab-pane label="训练数据" name="training-data">
        <template #label>
          <span class="tab-label"><el-icon><Document /></el-icon> 训练数据</span>
        </template>
      </el-tab-pane>
    </el-tabs>

    <!-- Search & Filter Bar -->
    <div class="filter-bar">
      <div class="search-box" :class="{ focused: isSearchFocused }">
        <el-icon class="search-icon"><Search /></el-icon>
        <input
          v-model="searchQuery"
          type="text"
          :placeholder="activeTab === 'adapters' ? '搜索风格名称、标签...' : '搜索标题...'"
          @focus="isSearchFocused = true"
          @blur="isSearchFocused = false"
          @keyup.enter="handleSearch"
        />
        <el-icon v-if="searchQuery" class="clear-btn" @click="searchQuery = ''; handleSearch()"><CircleClose /></el-icon>
      </div>

      <el-select v-model="sortBy" class="sort-select" @change="handleSearch">
        <el-option label="最新上传" value="upload_time" />
        <el-option label="总下载量" value="download_count" />
        <el-option v-if="activeTab === 'adapters'" label="周下载量" value="weekly_download_count" />
      </el-select>

      <el-select v-model="sortOrder" class="sort-select" @change="handleSearch">
        <el-option label="降序" value="desc" />
        <el-option label="升序" value="asc" />
      </el-select>

      <el-radio-group v-if="exploreStore.isLoggedIn" v-model="showMineOnly" size="default" @change="handleSearch">
        <el-radio-button :label="false">全部</el-radio-button>
        <el-radio-button :label="true">我的上传</el-radio-button>
      </el-radio-group>

      <el-button
        v-if="exploreStore.isLoggedIn"
        type="primary"
        :icon="Upload"
        @click="openUploadDialog"
      >
        上传{{ activeTab === 'adapters' ? 'Adapter' : '训练数据' }}
      </el-button>
    </div>

    <!-- Content List -->
    <div v-loading="exploreStore.loading" class="content-list">
      <!-- Adapter Cards -->
      <template v-if="activeTab === 'adapters'">
        <div v-if="adapters.length === 0" class="empty-state">
          <el-icon :size="64" color="#cbd5e1"><Box /></el-icon>
          <p>{{ showMineOnly ? '您还没有上传过 Adapter' : '暂无共享的 Adapter' }}</p>
        </div>
        <div v-else class="card-grid">
          <div
            v-for="item in adapters"
            :key="item.id"
            class="resource-card"
            @click="openAdapterDetail(item)"
          >
            <div class="card-header">
              <h3 class="card-title">{{ item.style_name }}</h3>
              <el-tag size="small">{{ item.style_tag }}</el-tag>
            </div>
            <p class="card-desc">{{ item.description || '无描述' }}</p>
            <div class="card-meta">
              <span><el-icon><SetUp /></el-icon> {{ item.base_model }}</span>
              <span><el-icon><Download /></el-icon> {{ item.download_count }}</span>
              <span v-if="item.overall_score !== null" class="score-badge">
                <el-icon><Star /></el-icon> {{ item.overall_score }}
              </span>
            </div>
            <div class="card-footer">
              <span class="uploader">{{ item.uploader_name }}</span>
              <span class="time">{{ formatTime(item.upload_time) }}</span>
              <div v-if="showMineOnly && isUploader(item)" class="card-actions">
                <el-button link size="small" :icon="Edit" @click.stop="openEditDialog(item)">编辑</el-button>
                <el-button link size="small" type="danger" :icon="Delete" @click.stop="handleDelete(item)">移除</el-button>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Training Data Cards -->
      <template v-else>
        <div v-if="trainingData.length === 0" class="empty-state">
          <el-icon :size="64" color="#cbd5e1"><Document /></el-icon>
          <p>{{ showMineOnly ? '您还没有上传过训练数据' : '暂无共享的训练数据' }}</p>
        </div>
        <div v-else class="card-grid">
          <div
            v-for="item in trainingData"
            :key="item.id"
            class="resource-card"
            @click="openTrainingDataDetail(item)"
          >
            <div class="card-header">
              <h3 class="card-title">{{ item.title }}</h3>
            </div>
            <p class="card-desc">{{ item.description || '无描述' }}</p>
            <div class="card-meta">
              <span><el-icon><Download /></el-icon> {{ item.download_count }}</span>
              <span><el-icon><Files /></el-icon> {{ formatFileSize(item.file_size) }}</span>
            </div>
            <div class="card-footer">
              <span class="uploader">{{ item.uploader_name }}</span>
              <span class="time">{{ formatTime(item.upload_time) }}</span>
              <div v-if="showMineOnly && isUploader(item)" class="card-actions">
                <el-button link size="small" :icon="Edit" @click.stop="openEditDialog(item)">编辑</el-button>
                <el-button link size="small" type="danger" :icon="Delete" @click.stop="handleDelete(item)">移除</el-button>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Pagination -->
    <div v-if="pagination.total > 0" class="pagination-wrapper">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[12, 24, 48]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next"
        background
        @change="handleSearch"
      />
    </div>

    <!-- Auth Dialog -->
    <el-dialog v-model="showAuthDialog" title="" width="420px" destroy-on-close>
      <div class="dialog-header-bar">
        <div class="dialog-icon">
          <el-icon :size="20"><User /></el-icon>
        </div>
        <span class="dialog-title">{{ authMode === 'login' ? '登录' : '注册' }}</span>
      </div>
      <div class="dialog-body">
        <el-form :model="authForm" label-position="top">
          <el-form-item label="用户名">
            <el-input v-model="authForm.username" placeholder="请输入用户名" />
          </el-form-item>
          <el-form-item v-if="authMode === 'register'" label="邮箱">
            <el-input v-model="authForm.email" placeholder="请输入邮箱" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="authForm.password" type="password" placeholder="请输入密码" show-password />
          </el-form-item>
        </el-form>
        <div class="auth-switch">
          <el-button link @click="authMode = authMode === 'login' ? 'register' : 'login'">
            {{ authMode === 'login' ? '没有账号？去注册' : '已有账号？去登录' }}
          </el-button>
        </div>
      </div>
      <template #footer>
        <el-button @click="showAuthDialog = false">取消</el-button>
        <el-button type="primary" :loading="exploreStore.loading" @click="handleAuth">
          {{ authMode === 'login' ? '登录' : '注册' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Upload Dialog -->
    <el-dialog v-model="showUploadDialog" title="" width="520px" destroy-on-close>
      <div class="dialog-header-bar">
        <div class="dialog-icon">
          <el-icon :size="20"><Upload /></el-icon>
        </div>
        <span class="dialog-title">上传{{ activeTab === 'adapters' ? 'Adapter' : '训练数据' }}</span>
      </div>
      <div class="dialog-body">
        <!-- Adapter Upload Form -->
        <template v-if="activeTab === 'adapters'">
          <el-form label-position="top">
            <el-form-item label="选择本地风格" required>
              <el-select
                v-model="selectedLocalStyle"
                placeholder="选择一个已训练完成的本地风格"
                style="width: 100%"
                @change="onLocalStyleSelected"
              >
                <el-option
                  v-for="s in localStyles"
                  :key="s.id"
                  :label="s.name + ' (' + s.target_style + ')'"
                  :value="s.id"
                />
              </el-select>
            </el-form-item>

            <div v-if="selectedLocalStyle" class="auto-fill-info">
              <div class="info-row">
                <span class="info-label">风格名称</span>
                <span class="info-value">{{ adapterForm.style_name }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">风格标签</span>
                <span class="info-value">{{ adapterForm.style_tag }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">底座模型</span>
                <span class="info-value">{{ adapterForm.base_model }}</span>
              </div>
            </div>

            <el-form-item label="描述">
              <el-input
                v-model="adapterForm.description"
                type="textarea"
                :rows="3"
                placeholder="补充描述（可选），将覆盖本地描述"
                maxlength="2000"
                show-word-limit
              />
            </el-form-item>
          </el-form>
        </template>

        <!-- Training Data Upload Form -->
        <template v-else>
          <el-form :model="trainingDataForm" label-position="top">
            <el-form-item label="标题" required>
              <el-input v-model="trainingDataForm.title" placeholder="输入标题" maxlength="100" show-word-limit />
            </el-form-item>
            <el-form-item label="描述">
              <el-input v-model="trainingDataForm.description" type="textarea" :rows="3" placeholder="描述这份训练数据..." maxlength="2000" show-word-limit />
            </el-form-item>
            <el-form-item label="文件 (.txt/.csv/.json/.jsonl)" required>
              <el-upload
                ref="tdUploadRef"
                :auto-upload="false"
                :limit="1"
                :on-change="handleTdFileChange"
                :on-remove="() => tdFile = null"
                accept=".txt,.csv,.json,.jsonl"
              >
                <el-button type="primary">选择文件</el-button>
              </el-upload>
            </el-form-item>
          </el-form>
        </template>
      </div>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" :loading="exploreStore.loading" @click="handleUpload">
          上传
        </el-button>
      </template>
    </el-dialog>

    <!-- Adapter Detail Drawer -->
    <el-drawer v-model="adapterDrawerVisible" :title="currentAdapter?.style_name" size="760px">
      <div v-if="currentAdapter" class="detail-content">
        <div class="detail-meta">
          <el-tag size="small">{{ currentAdapter.style_tag }}</el-tag>
          <el-tag size="small" type="info">{{ currentAdapter.base_model }}</el-tag>
          <span class="detail-stat"><el-icon><Download /></el-icon> {{ currentAdapter.download_count }} 次下载</span>
          <span class="detail-stat">{{ currentAdapter.uploader_name }}</span>
          <span class="detail-stat">{{ formatTime(currentAdapter.upload_time) }}</span>
        </div>
        <p class="detail-desc">{{ currentAdapter.description || '无描述' }}</p>

        <div class="detail-actions"
          :class="{ 'detail-actions-multiple': showMineOnly && currentAdapter && isUploader(currentAdapter) }"
        >
          <template v-if="showMineOnly && currentAdapter && isUploader(currentAdapter)"
          >
            <el-button size="large" @click="openEditDialog(currentAdapter)"
            >
              <el-icon><Edit /></el-icon>
              编辑信息
            </el-button>
            <el-button type="danger" size="large" @click="handleDelete(currentAdapter)"
            >
              <el-icon><Delete /></el-icon>
              移除
            </el-button>
          </template>
          <el-button type="primary" size="large" @click="handlePullAdapter"
          >
            <el-icon><Download /></el-icon>
            拉取到本地
          </el-button>
        </div>

        <!-- Evaluation Report -->
        <div v-if="currentAdapter.evaluation_results" class="evaluation-section">
          <h4>评估结果</h4>
          <EvaluationReport
            :data="formatEvaluationData(currentAdapter)"
            :show-actions="false"
            :show-comment="false"
          />
        </div>
      </div>
    </el-drawer>

    <!-- Training Data Detail Drawer -->
    <el-drawer v-model="tdDrawerVisible" :title="currentTrainingData?.title" size="760px">
      <div v-if="currentTrainingData" class="detail-content">
        <div class="detail-meta">
          <span class="detail-stat"><el-icon><Download /></el-icon> {{ currentTrainingData.download_count }} 次下载</span>
          <span class="detail-stat">{{ currentTrainingData.uploader_name }}</span>
          <span class="detail-stat">{{ formatTime(currentTrainingData.upload_time) }}</span>
        </div>
        <p class="detail-desc">{{ currentTrainingData.description || '无描述' }}</p>

        <div class="detail-actions"
          :class="{ 'detail-actions-multiple': showMineOnly && currentTrainingData && isUploader(currentTrainingData) }"
        >
          <template v-if="showMineOnly && currentTrainingData && isUploader(currentTrainingData)"
          >
            <el-button size="large" @click="openEditDialog(currentTrainingData)"
            >
              <el-icon><Edit /></el-icon>
              编辑信息
            </el-button>
            <el-button type="danger" size="large" @click="handleDelete(currentTrainingData)"
            >
              <el-icon><Delete /></el-icon>
              移除
            </el-button>
          </template>
          <el-button type="primary" size="large" @click="exploreStore.downloadTrainingData(currentTrainingData)"
          >
            <el-icon><Download /></el-icon>
            下载到本地
          </el-button>
        </div>

        <!-- Preview -->
        <div class="preview-section">
          <div class="preview-header">
            <h4>内容预览</h4>
            <el-button size="small" @click="loadPreview">刷新预览</el-button>
          </div>
          <div v-loading="previewLoading" class="preview-content">
            <pre v-if="previewLines.length > 0">{{ previewLines.join('\n') }}</pre>
            <p v-else class="preview-empty">点击刷新预览</p>
            <p v-if="previewHasMore" class="preview-more">...还有更多内容</p>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- Edit Dialog -->
    <el-dialog v-model="showEditDialog" title="" width="520px" destroy-on-close>
      <div class="dialog-header-bar">
        <div class="dialog-icon">
          <el-icon :size="20"><Edit /></el-icon>
        </div>
        <span class="dialog-title">编辑{{ activeTab === 'adapters' ? 'Adapter' : '训练数据' }}</span>
      </div>
      <div class="dialog-body">
        <template v-if="activeTab === 'adapters'"
        >
          <el-form label-position="top"
          >
            <el-form-item label="风格名称" required>
              <el-input v-model="editAdapterForm.style_name" placeholder="风格名称" maxlength="100" show-word-limit />
            </el-form-item>
            <el-form-item label="风格标签" required>
              <el-input v-model="editAdapterForm.style_tag" placeholder="风格标签" maxlength="50" show-word-limit />
            </el-form-item>
            <el-form-item label="底座模型" required>
              <el-input v-model="editAdapterForm.base_model" placeholder="底座模型" maxlength="50" show-word-limit />
            </el-form-item>
            <el-form-item label="描述">
              <el-input
                v-model="editAdapterForm.description"
                type="textarea"
                :rows="3"
                placeholder="描述"
                maxlength="2000"
                show-word-limit
              />
            </el-form-item>
          </el-form>
        </template>
        <template v-else
        >
          <el-form label-position="top"
          >
            <el-form-item label="标题" required>
              <el-input v-model="editTrainingDataForm.title" placeholder="标题" maxlength="100" show-word-limit />
            </el-form-item>
            <el-form-item label="描述">
              <el-input
                v-model="editTrainingDataForm.description"
                type="textarea"
                :rows="3"
                placeholder="描述"
                maxlength="2000"
                show-word-limit
              />
            </el-form-item>
          </el-form>
        </template>
      </div>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="exploreStore.loading" @click="handleEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { useExploreStore } from '@/stores/explore'
import EvaluationReport from '@/components/Evaluation/EvaluationReport.vue'
import {
  Compass, User, Cpu, Document, Search, CircleClose,
  Upload, Download, Star, SetUp, Box, Files, Edit, Delete
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'

const exploreStore = useExploreStore()

const activeTab = ref('adapters')
const searchQuery = ref('')
const sortBy = ref('upload_time')
const sortOrder = ref('desc')
const currentPage = ref(1)
const pageSize = ref(12)
const isSearchFocused = ref(false)
const pagination = reactive({ total: 0, page: 1, page_size: 12, total_pages: 0 })

const adapters = ref([])
const trainingData = ref([])

// Auth dialog
const showAuthDialog = ref(false)
const authMode = ref('login')
const authForm = reactive({ username: '', email: '', password: '' })

// Upload dialog
const showUploadDialog = ref(false)
const adapterForm = reactive({ style_name: '', style_tag: '', description: '', base_model: '' })
const trainingDataForm = reactive({ title: '', description: '' })
const localStyles = ref([])
const selectedLocalStyle = ref('')
const tdFile = ref(null)
const tdUploadRef = ref(null)

// Detail drawers
const adapterDrawerVisible = ref(false)
const tdDrawerVisible = ref(false)
const currentAdapter = ref(null)
const currentTrainingData = ref(null)

// Mine toggle
const showMineOnly = ref(false)

// Edit dialog
const showEditDialog = ref(false)
const editAdapterForm = reactive({ id: '', style_name: '', style_tag: '', description: '', base_model: '' })
const editTrainingDataForm = reactive({ id: '', title: '', description: '' })

// Preview
const previewLines = ref([])
const previewHasMore = ref(false)
const previewLoading = ref(false)

const currentUserId = computed(() => exploreStore.user?.id || null)

onMounted(() => {
  exploreStore.fetchUser()
  loadData()
})

watch(activeTab, () => {
  searchQuery.value = ''
  sortBy.value = 'upload_time'
  currentPage.value = 1
  loadData()
})

function openUploadDialog() {
  if (activeTab.value === 'adapters') {
    loadLocalStyles()
    selectedLocalStyle.value = ''
    adapterForm.style_name = ''
    adapterForm.style_tag = ''
    adapterForm.base_model = ''
    adapterForm.description = ''
  }
  showUploadDialog.value = true
}

async function loadData() {
  const params = {
    search: searchQuery.value || undefined,
    sort_by: sortBy.value,
    sort_order: sortOrder.value,
    page: currentPage.value,
    page_size: pageSize.value,
    mine: showMineOnly.value,
  }

  if (activeTab.value === 'adapters') {
    const res = await exploreStore.fetchAdapters(params)
    adapters.value = res?.items || []
    Object.assign(pagination, res?.pagination || { total: 0 })
  } else {
    const res = await exploreStore.fetchTrainingData(params)
    trainingData.value = res?.items || []
    Object.assign(pagination, res?.pagination || { total: 0 })
  }
}

function isUploader(item) {
  return currentUserId.value && item.uploader_id === currentUserId.value
}

function openEditDialog(item) {
  if (activeTab.value === 'adapters') {
    editAdapterForm.id = item.id
    editAdapterForm.style_name = item.style_name
    editAdapterForm.style_tag = item.style_tag
    editAdapterForm.description = item.description || ''
    editAdapterForm.base_model = item.base_model
  } else {
    editTrainingDataForm.id = item.id
    editTrainingDataForm.title = item.title
    editTrainingDataForm.description = item.description || ''
  }
  showEditDialog.value = true
}

async function handleEdit() {
  if (activeTab.value === 'adapters') {
    await exploreStore.updateAdapter(editAdapterForm.id, {
      style_name: editAdapterForm.style_name,
      style_tag: editAdapterForm.style_tag,
      description: editAdapterForm.description,
      base_model: editAdapterForm.base_model,
    })
  } else {
    await exploreStore.updateTrainingData(editTrainingDataForm.id, {
      title: editTrainingDataForm.title,
      description: editTrainingDataForm.description,
    })
  }
  showEditDialog.value = false
  loadData()
}

async function handleDelete(item) {
  try {
    await ElMessageBox.confirm(
      `确定要移除 "${activeTab.value === 'adapters' ? item.style_name : item.title}" 吗？`,
      '确认移除',
      { confirmButtonText: '移除', cancelButtonText: '取消', type: 'warning' }
    )
    if (activeTab.value === 'adapters') {
      await exploreStore.deleteAdapter(item.id)
    } else {
      await exploreStore.deleteTrainingData(item.id)
    }
    loadData()
  } catch {
    // cancelled
  }
}

function handleSearch() {
  currentPage.value = 1
  loadData()
}

async function handleAuth() {
  if (authMode.value === 'login') {
    await exploreStore.login({
      username: authForm.username,
      password: authForm.password,
    })
  } else {
    await exploreStore.register({
      username: authForm.username,
      email: authForm.email,
      password: authForm.password,
    })
  }
  showAuthDialog.value = false
  authForm.username = ''
  authForm.email = ''
  authForm.password = ''
}

function handleTdFileChange(file) {
  tdFile.value = file.raw
}

async function loadLocalStyles() {
  try {
    const client = axios.create({ baseURL: '', timeout: 30000 })
    const res = await client.get('/api/styles', { params: { page_size: 100 } })
    const items = res.data?.data?.items || []
    localStyles.value = items.filter(s => s.status === 'available' || s.status === 'completed')
  } catch (error) {
    console.error('Failed to load local styles:', error)
  }
}

function onLocalStyleSelected(styleId) {
  const style = localStyles.value.find(s => s.id === styleId)
  if (style) {
    adapterForm.style_name = style.name
    adapterForm.style_tag = style.target_style
    adapterForm.base_model = style.base_model
    adapterForm.description = style.description || ''
  }
}

async function handleUpload() {
  if (activeTab.value === 'adapters') {
    if (!selectedLocalStyle.value) {
      ElMessage.warning('请选择一个本地风格')
      return
    }
    if (!exploreStore.token) {
      ElMessage.warning('请先登录')
      showAuthDialog.value = true
      return
    }
    await exploreStore.uploadAdapterToCloud({
      styleId: selectedLocalStyle.value,
      description: adapterForm.description,
    })
    selectedLocalStyle.value = ''
    showUploadDialog.value = false
    loadData()
  } else {
    if (!tdFile.value) {
      ElMessage.warning('请选择文件')
      return
    }
    const formData = new FormData()
    formData.append('title', trainingDataForm.title)
    formData.append('description', trainingDataForm.description)
    formData.append('file', tdFile.value)
    await exploreStore.uploadTrainingData(formData)
    tdUploadRef.value?.clearFiles()
    tdFile.value = null
    showUploadDialog.value = false
    loadData()
  }
}

function openAdapterDetail(item) {
  currentAdapter.value = item
  adapterDrawerVisible.value = true
}

function openTrainingDataDetail(item) {
  currentTrainingData.value = item
  tdDrawerVisible.value = true
  previewLines.value = []
  previewHasMore.value = false
  loadPreview()
}

async function loadPreview() {
  if (!currentTrainingData.value) return
  previewLoading.value = true
  try {
    const data = await exploreStore.previewTrainingData(currentTrainingData.value.id, 50)
    previewLines.value = data?.preview_lines || []
    previewHasMore.value = data?.has_more || false
  } finally {
    previewLoading.value = false
  }
}

async function handlePullAdapter() {
  if (!currentAdapter.value) return
  await exploreStore.pullAdapterToLocal(currentAdapter.value)
}

function formatEvaluationData(adapter) {
  const evalData = adapter.evaluation_results || {}
  return {
    task_name: adapter.style_name,
    target_style: adapter.style_tag,
    generated_at: formatTime(adapter.upload_time),
    overall_score: evalData.overall_score || 0,
    sample_count: evalData.sample_count || 0,
    char_retention: evalData.char_retention || 0,
    style_score: evalData.style_score || 0,
    fluency_score: evalData.fluency_score || 0,
    vocab_diversity: evalData.vocab_diversity || 0,
    length_ratio: evalData.length_ratio || 0,
    bleu_score: evalData.bleu_score || 0,
    bert_score: evalData.bert_score || 0,
    avg_response_time: evalData.avg_response_time || 0,
    samples: evalData.samples || [],
    comment: evalData.comment || null,
    task_id: adapter.id,
  }
}

function formatTime(time) {
  if (!time) return '-'
  return dayjs(time).format('YYYY-MM-DD HH:mm')
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
</script>

<style scoped>
.explore-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
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
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 0 20px rgba(245, 158, 11, 0.3);
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* Tabs */
.explore-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Filter Bar */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding: 12px 20px;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
}

.search-box {
  position: relative;
  flex: 1;
  max-width: 320px;
  background: var(--bg-secondary);
  border-radius: 10px;
  border: 1px solid var(--border-color);
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
}

.search-box.focused {
  border-color: #f59e0b;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.1);
}

.search-icon {
  margin-left: 12px;
  color: var(--text-muted);
  font-size: 16px;
}

.search-box input {
  flex: 1;
  padding: 9px 32px 9px 8px;
  border: none;
  background: transparent;
  font-size: 14px;
  color: var(--text-primary);
  outline: none;
}

.search-box input::placeholder {
  color: var(--text-muted);
}

.clear-btn {
  position: absolute;
  right: 8px;
  cursor: pointer;
  color: var(--text-muted);
  padding: 4px;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.clear-btn:hover {
  background: var(--bg-card);
  color: var(--text-primary);
}

.sort-select {
  width: 140px;
}

/* Content List */
.content-list {
  flex: 1;
  min-height: 300px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
}

.empty-state p {
  color: var(--text-secondary);
  margin-top: 16px;
  font-size: 16px;
}

/* Card Grid */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.resource-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.resource-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
  border-color: rgba(245, 158, 11, 0.3);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.card-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0 0 12px;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  min-height: 40px;
}

.card-meta {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--text-muted);
}

.card-meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.score-badge {
  color: #f59e0b;
  font-weight: 600;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--text-muted);
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.card-actions {
  display: flex;
  gap: 4px;
}

/* Pagination */
.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 24px 0;
}

/* Dialog */
.dialog-header-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  margin: -20px -20px 20px;
  border-radius: 6px;
}

.dialog-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
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
  padding: 0 4px;
}

.auto-fill-info {
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  margin-bottom: 16px;
  border: 1px solid var(--border-color);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  font-size: 13px;
}

.info-row:not(:last-child) {
  border-bottom: 1px solid var(--border-color);
}

.info-label {
  color: var(--text-muted);
  font-weight: 500;
}

.info-value {
  color: var(--text-primary);
  font-weight: 600;
  text-align: right;
  max-width: 60%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.auth-switch {
  text-align: center;
  margin-top: 8px;
}

/* Detail Drawer */
.detail-content {
  padding: 4px 8px 20px;
}

.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
  align-items: center;
}

.detail-stat {
  font-size: 13px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 4px;
}

.detail-desc {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 16px;
  padding: 14px 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.evaluation-section {
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.evaluation-section h4 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.detail-actions {
  margin-top: 0;
  display: flex;
  justify-content: flex-start;
  gap: 12px;
}

.detail-actions-multiple {
  flex-wrap: wrap;
}

/* Preview */
.preview-section {
  margin-top: 16px;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.preview-header h4 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.preview-content {
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  padding: 16px;
  border: 1px solid var(--border-color);
  max-height: 400px;
  overflow-y: auto;
}

.preview-content pre {
  margin: 0;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-all;
}

.preview-empty {
  text-align: center;
  color: var(--text-muted);
  margin: 20px 0;
}

.preview-more {
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
  margin-top: 8px;
  font-style: italic;
}

/* Responsive */
@media (max-width: 768px) {
  .filter-bar {
    flex-wrap: wrap;
  }

  .search-box {
    max-width: none;
    flex: 1 1 100%;
  }

  .card-grid {
    grid-template-columns: 1fr;
  }
}
</style>
