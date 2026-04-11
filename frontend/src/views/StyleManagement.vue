<template>
  <div class="page-container">
    <div class="page-header">
      <h1>风格管理</h1>
      <p>查看和管理所有已创建的风格</p>
    </div>

    <div class="management-container">
      <!-- Toolbar -->
      <div class="toolbar">
        <el-input
          v-model="searchQuery"
          placeholder="搜索风格名称"
          clearable
          style="width: 300px"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-button type="primary" :icon="Plus" @click="showCreateDialog">
          新建风格
        </el-button>
      </div>

      <!-- Styles Grid -->
      <div v-loading="styleStore.loading" class="styles-grid">
        <el-card
          v-for="style in filteredStyles"
          :key="style.id"
          class="style-card"
          shadow="hover"
        >
          <div class="style-header">
            <h3>{{ style.name }}</h3>
            <el-tag
              :type="getStatusType(style.status)"
              size="small"
            >
              {{ getStatusLabel(style.status) }}
            </el-tag>
          </div>

          <p class="style-description">
            {{ style.description || '暂无描述' }}
          </p>

          <div class="style-meta">
            <div class="meta-item">
              <span class="label">目标风格:</span>
              <span class="value">{{ style.target_style }}</span>
            </div>
            <div class="meta-item">
              <span class="label">创建时间:</span>
              <span class="value">{{ formatTime(style.created_at) }}</span>
            </div>
          </div>

          <div class="style-actions">
            <el-button
              link
              type="primary"
              :icon="Edit"
              @click="editStyle(style)"
              :disabled="style.status === 'training'"
            >
              编辑
            </el-button>

            <el-popconfirm
              title="确定要删除这个风格吗？"
              confirm-button-text="确定"
              cancel-button-text="取消"
              @confirm="deleteStyle(style.id)"
            >
              <template #reference>
                <el-button
                  link
                  type="danger"
                  :icon="Delete"
                  :disabled="style.status === 'training'"
                >
                  删除
                </el-button>
              </template>
            </el-popconfirm>
          </div>
        </el-card>
      </div>

      <!-- Pagination -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="styleStore.styles.length"
          layout="total, sizes, prev, pager, next"
        />
      </div>
    </div>

    <!-- Edit Dialog -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑风格"
      width="500px"
    >
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="风格名称">
          <el-input v-model="editForm.name" />
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

        <el-form-item label="底座模型">
          <el-input v-model="editForm.base_model" disabled />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit" :loading="saving">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- Create Dialog -->
    <el-dialog
      v-model="createDialogVisible"
      title="新建风格"
      width="500px"
    >
      <el-form :model="createForm" label-width="80px" :rules="createRules" ref="createFormRef">
        <el-form-item label="风格名称" prop="name">
          <el-input v-model="createForm.name" placeholder="例如：幽默风格" />
        </el-form-item>

        <el-form-item label="风格描述">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="描述这个风格的特点..."
          />
        </el-form-item>

        <el-form-item label="目标风格" prop="target_style">
          <el-input v-model="createForm.target_style" placeholder="例如：幽默、学术" />
        </el-form-item>

        <el-form-item label="底座模型">
          <el-radio-group v-model="createForm.base_model">
            <el-radio-button label="llama-2-3b">LLaMA-2-3B</el-radio-button>
            <el-radio-button label="chatglm3-6b">ChatGLM3-6B</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveCreate" :loading="creating">
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useStyleStore } from '@/stores/style'
import {
  Search,
  Plus,
  Edit,
  Delete
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const styleStore = useStyleStore()

const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

// Edit dialog
const editDialogVisible = ref(false)
const editForm = reactive({
  id: '',
  name: '',
  description: '',
  target_style: '',
  base_model: ''
})
const saving = ref(false)

// Create dialog
const createDialogVisible = ref(false)
const createFormRef = ref(null)
const createForm = reactive({
  name: '',
  description: '',
  target_style: '',
  base_model: 'llama-2-3b'
})
const creating = ref(false)

const createRules = {
  name: [
    { required: true, message: '请输入风格名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  target_style: [
    { required: true, message: '请输入目标风格', trigger: 'blur' }
  ]
}

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

function getStatusType(status) {
  const types = {
    'pending': 'info',
    'training': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'available': 'success'
  }
  return types[status] || 'info'
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

function formatTime(time) {
  return dayjs(time).format('YYYY-MM-DD HH:mm')
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

async function deleteStyle(id) {
  try {
    await styleStore.deleteStyle(id)
    ElMessage.success('删除成功')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

function showCreateDialog() {
  Object.assign(createForm, {
    name: '',
    description: '',
    target_style: '',
    base_model: 'llama-2-3b'
  })
  createDialogVisible.value = true
}

async function saveCreate() {
  const valid = await createFormRef.value.validate().catch(() => false)
  if (!valid) return

  creating.value = true
  try {
    await styleStore.createStyle(createForm)
    ElMessage.success('创建成功')
    createDialogVisible.value = false
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
.page-container {
  max-width: 1200px;
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

.toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

.styles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.style-card {
  transition: all 0.3s ease;
}

.style-card:hover {
  transform: translateY(-2px);
}

.style-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.style-header h3 {
  margin: 0;
  font-size: 18px;
  color: #1a1a2e;
}

.style-description {
  color: #666;
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 16px;
  min-height: 40px;
}

.style-meta {
  margin-bottom: 16px;
}

.meta-item {
  display: flex;
  margin-bottom: 4px;
  font-size: 13px;
}

.meta-item .label {
  color: #909399;
  min-width: 70px;
}

.meta-item .value {
  color: #606266;
}

.style-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #e4e7ed;
}

.pagination {
  display: flex;
  justify-content: center;
}
</style>
