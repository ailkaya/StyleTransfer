<template>
  <div class="config-management-page">
    <!-- Header -->
    <div class="config-header">
      <div class="header-left">
        <el-icon :size="20"><Setting /></el-icon>
        <span class="header-title">配置管理</span>
        <el-tag v-if="envPath" size="small" type="info" effect="plain">
          {{ envPath }}
        </el-tag>
      </div>
      <div class="header-right">
        <el-input
          v-model="searchQuery"
          placeholder="搜索配置项..."
          clearable
          class="search-input"
          :prefix-icon="Search"
        />
        <el-button
          type="primary"
          :icon="Plus"
          :loading="saving"
          @click="handleSave"
        >
          保存更改
        </el-button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="10" animated />
    </div>

    <!-- Config Content -->
    <div v-else class="config-content">
      <el-empty v-if="filteredCategories.length === 0" description="未找到匹配的配置项" />

      <el-collapse v-else v-model="activeCategories" class="config-collapse">
        <el-collapse-item
          v-for="category in filteredCategories"
          :key="category.name"
          :name="category.name"
          class="category-item"
        >
          <template #title>
            <div class="category-header">
              <span class="category-label">{{ category.label }}</span>
              <el-tag size="small" type="info" effect="plain">
                {{ category.items.length }} 项
              </el-tag>
              <el-tag
                v-if="getModifiedCountInCategory(category) > 0"
                size="small"
                type="warning"
                effect="light"
                class="modified-tag"
              >
                {{ getModifiedCountInCategory(category) }} 项已修改
              </el-tag>
            </div>
          </template>

          <div class="config-items">
            <div
              v-for="item in category.items"
              :key="item.key"
              class="config-item"
              :class="{ 'is-modified': item.is_modified }"
            >
              <div class="item-info">
                <div class="item-header">
                  <span class="item-key">{{ item.key }}</span>
                  <div class="item-badges">
                    <el-tag
                      v-if="item.requires_restart"
                      size="small"
                      type="danger"
                      effect="plain"
                    >
                      <el-icon :size="12"><RefreshRight /></el-icon>
                      需重启
                    </el-tag>
                    <el-tag
                      v-if="item.is_sensitive"
                      size="small"
                      type="warning"
                      effect="plain"
                    >
                      <el-icon :size="12"><Lock /></el-icon>
                      敏感
                    </el-tag>
                    <el-tag
                      v-if="item.is_modified"
                      size="small"
                      type="success"
                      effect="light"
                    >
                      已修改
                    </el-tag>
                  </div>
                </div>
                <p v-if="item.description" class="item-description">
                  {{ item.description }}
                </p>
              </div>

              <div class="item-value">
                <!-- Boolean Type -->
                <el-switch
                  v-if="item.value_type === 'boolean'"
                  v-model="item.currentValue"
                  active-text="true"
                  inactive-text="false"
                  @change="handleValueChange(item)"
                />

                <!-- Integer Type -->
                <el-input-number
                  v-else-if="item.value_type === 'integer'"
                  v-model="item.currentValue"
                  :min="0"
                  :step="1"
                  controls-position="right"
                  style="width: 180px"
                  @change="handleValueChange(item)"
                />

                <!-- Float Type -->
                <el-input-number
                  v-else-if="item.value_type === 'float'"
                  v-model="item.currentValue"
                  :min="0"
                  :step="0.01"
                  :precision="2"
                  controls-position="right"
                  style="width: 180px"
                  @change="handleValueChange(item)"
                />

                <!-- Secret/Password Type -->
                <el-input
                  v-else-if="item.value_type === 'secret'"
                  v-model="item.currentValue"
                  type="password"
                  show-password
                  placeholder="请输入新值"
                  style="width: 280px"
                  @change="handleValueChange(item)"
                />

                <!-- String Type -->
                <el-input
                  v-else
                  v-model="item.currentValue"
                  :type="isLongText(item.value) ? 'textarea' : 'text'"
                  :rows="isLongText(item.value) ? 3 : 1"
                  clearable
                  style="width: 280px"
                  @change="handleValueChange(item)"
                />

                <el-button
                  v-if="item.is_modified"
                  type="info"
                  link
                  size="small"
                  :icon="RefreshLeft"
                  @click="handleReset(item)"
                >
                  重置
                </el-button>
              </div>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>

    <!-- Save Confirmation Dialog -->
    <el-dialog
      v-model="showConfirmDialog"
      title="确认保存更改"
      width="500px"
      :close-on-click-modal="false"
    >
      <div class="confirm-content">
        <!-- Has changes -->
        <template v-if="modifiedItems.length > 0">
          <p>以下 {{ modifiedItems.length }} 个配置项将被更新：</p>
          <el-scrollbar max-height="300px" class="modified-list">
            <div
              v-for="item in modifiedItems"
              :key="item.key"
              class="modified-item"
            >
              <div class="modified-key">{{ item.key }}</div>
              <div class="modified-value">
                <span class="old-value">{{ maskValue(item.originalValue, item.is_sensitive) }}</span>
                <el-icon class="arrow-icon"><ArrowRight /></el-icon>
                <span class="new-value">{{ maskValue(item.currentValue, item.is_sensitive) }}</span>
              </div>
            </div>
          </el-scrollbar>

          <el-alert
            v-if="modifiedItems.some(i => i.requires_restart)"
            type="warning"
            :closable="false"
            show-icon
            class="restart-notice"
          >
            <template #title>
              <span>部分配置修改后需要重启服务才能生效</span>
            </template>
          </el-alert>
        </template>

        <!-- No changes -->
        <template v-else>
          <el-empty description="没有配置项被修改" :image-size="80">
            <p class="no-change-hint">您还没有修改任何配置项</p>
          </el-empty>
        </template>
      </div>

      <template #footer>
        <el-button @click="showConfirmDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="saving"
          :disabled="modifiedItems.length === 0"
          @click="confirmSave"
        >
          确认保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import {
  Setting,
  Search,
  Plus,
  RefreshRight,
  Lock,
  RefreshLeft,
  ArrowRight,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { configApi } from '@/api/config'

// State
const loading = ref(false)
const saving = ref(false)
const categories = ref([])
const envPath = ref('')
const searchQuery = ref('')
const activeCategories = ref([])
const showConfirmDialog = ref(false)

// Flatten all items for tracking changes (use ref with object for better reactivity)
const allItems = ref(new Map())

// Computed
const filteredCategories = computed(() => {
  if (!searchQuery.value.trim()) {
    return categories.value
  }

  const query = searchQuery.value.toLowerCase()
  return categories.value
    .map(cat => ({
      ...cat,
      items: cat.items.filter(item =>
        item.key.toLowerCase().includes(query) ||
        (item.description && item.description.toLowerCase().includes(query))
      )
    }))
    .filter(cat => cat.items.length > 0)
})

// Computed: items that have been modified (used in dialog)
const modifiedItems = computed(() => {
  return Array.from(allItems.value.values()).filter(item => item.is_modified)
})

// Methods
function isLongText(value) {
  return value && (value.length > 50 || value.includes('\n'))
}

function maskValue(value, isSensitive) {
  // Convert value to string for display
  const strValue = value !== null && value !== undefined ? String(value) : ''
  if (!strValue) {
    return '(空)'
  }
  if (!isSensitive || strValue.length <= 8) {
    return strValue
  }
  return `${strValue.slice(0, 4)}****${strValue.slice(-4)}`
}

function getModifiedCountInCategory(category) {
  return category.items.filter(item => item.is_modified).length
}

function handleValueChange(item) {
  const trackedItem = allItems.value.get(item.key)
  if (trackedItem) {
    // Compare string representations to handle type differences (e.g., boolean vs string)
    const currentStr = String(trackedItem.currentValue)
    trackedItem.is_modified = currentStr !== trackedItem.originalValue
    // Force trigger reactivity by reassigning the Map
    allItems.value = new Map(allItems.value)
  }
}

function handleReset(item) {
  const trackedItem = allItems.value.get(item.key)
  if (trackedItem) {
    const originalValue = trackedItem.originalValue
    // Convert back to appropriate type for the input
    if (item.value_type === 'boolean') {
      trackedItem.currentValue = originalValue === 'true'
    } else if (item.value_type === 'integer') {
      trackedItem.currentValue = parseInt(originalValue, 10) || 0
    } else if (item.value_type === 'float') {
      trackedItem.currentValue = parseFloat(originalValue) || 0
    } else {
      trackedItem.currentValue = originalValue
    }
    trackedItem.is_modified = false
    // Force trigger reactivity by reassigning the Map
    allItems.value = new Map(allItems.value)
  }
}

function handleSave() {
  // Real-time comparison: mark items as modified if current value differs from original
  allItems.value.forEach(item => {
    const currentStr = String(item.currentValue)
    item.is_modified = currentStr !== item.originalValue
  })
  // Refresh the dialog content
  showConfirmDialog.value = true
}

async function confirmSave() {
  saving.value = true
  try {
    const configsToUpdate = modifiedItems.value.map(item => ({
      key: item.key,
      value: String(item.currentValue)
    }))

    const res = await configApi.updateConfig(configsToUpdate)

    if (res.code === 200) {
      ElMessage.success('配置保存成功')

      // Update original values and reset modification state
      modifiedItems.value.forEach(item => {
        item.originalValue = String(item.currentValue)
        item.is_modified = false
      })

      showConfirmDialog.value = false

      // Show restart hint if needed
      if (res.data?.updated?.some(key => {
        const item = allItems.value.get(key)
        return item?.requires_restart
      })) {
        ElMessage.warning('部分配置需要重启服务才能生效')
      }
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch (error) {
    console.error('Failed to save config:', error)
    ElMessage.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function fetchConfig() {
  loading.value = true
  try {
    const res = await configApi.getConfig()

    if (res.code === 200 && res.data) {
      envPath.value = res.data.env_path || ''

      // Process categories and track items
      categories.value = res.data.categories || []

      // Clear and repopulate tracked items
      allItems.value.clear()

      categories.value.forEach(category => {
        category.items = category.items.map(item => {
          // Initialize current value from value or raw_value
          const initialValue = item.raw_value !== null && item.raw_value !== undefined
            ? item.raw_value
            : item.value

          // Add tracking properties to the item itself
          item.originalValue = initialValue
          item.currentValue = initialValue
          item.is_modified = false

          // Type conversion for form inputs
          if (item.value_type === 'boolean') {
            item.currentValue = initialValue === 'true'
          } else if (item.value_type === 'integer') {
            item.currentValue = parseInt(initialValue, 10) || 0
          } else if (item.value_type === 'float') {
            item.currentValue = parseFloat(initialValue) || 0
          }

          // Store in map (same object reference as in array)
          allItems.value.set(item.key, item)

          return item
        })
      })
      // Force reactivity update after populating Map
      allItems.value = new Map(allItems.value)

      // Expand first category by default
      if (categories.value.length > 0) {
        activeCategories.value = [categories.value[0].name]
      }
    } else {
      ElMessage.error(res.message || '获取配置失败')
    }
  } catch (error) {
    console.error('Failed to fetch config:', error)
    ElMessage.error(error.message || '获取配置失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchConfig()
})
</script>

<style scoped>
.config-management-page {
  height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
}

.config-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  margin-bottom: 12px;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--text-primary);
}

.header-title {
  font-size: 16px;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-input {
  width: 240px;
}

.restart-alert {
  margin-bottom: 12px;
}

.loading-state {
  flex: 1;
  padding: 20px;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
}

.config-content {
  flex: 1;
  overflow-y: auto;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  padding: 16px;
}

.config-collapse {
  border: none;
}

:deep(.config-collapse .el-collapse-item__header) {
  font-size: 14px;
  font-weight: 600;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

:deep(.config-collapse .el-collapse-item__content) {
  padding: 0;
}

.category-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.category-label {
  color: var(--text-primary);
}

.modified-tag {
  margin-left: auto;
}

.config-items {
  padding: 8px 0;
}

.config-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
  transition: background-color 0.2s;
}

.config-item:last-child {
  border-bottom: none;
}

.config-item:hover {
  background: var(--bg-secondary);
}

.config-item.is-modified {
  background: rgba(16, 185, 129, 0.05);
}

.item-info {
  flex: 1;
  min-width: 0;
  margin-right: 20px;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.item-key {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: 'Monaco', 'Consolas', monospace;
}

.item-badges {
  display: flex;
  gap: 6px;
}

.item-description {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 4px 0 0;
  line-height: 1.5;
}

.item-value {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

/* Confirm Dialog Styles */
.confirm-content {
  padding: 10px 0;
}

.confirm-content > p {
  margin-bottom: 16px;
  color: var(--text-primary);
}

.modified-list {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
}

.modified-item {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.modified-item:last-child {
  border-bottom: none;
}

.modified-key {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: 'Monaco', 'Consolas', monospace;
  margin-bottom: 6px;
}

.modified-value {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.old-value {
  color: var(--text-muted);
  text-decoration: line-through;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.arrow-icon {
  color: var(--primary-color);
}

.new-value {
  color: var(--success-color);
  font-weight: 500;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.restart-notice {
  margin-top: 16px;
}

.no-change-hint {
  color: var(--text-secondary);
  font-size: 13px;
  margin-top: 8px;
}

/* Responsive */
@media (max-width: 768px) {
  .config-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .header-right {
    width: 100%;
  }

  .search-input {
    flex: 1;
  }

  .config-item {
    flex-direction: column;
    gap: 12px;
  }

  .item-info {
    margin-right: 0;
  }

  .item-value {
    width: 100%;
  }

  .item-value :deep(.el-input),
  .item-value :deep(.el-input-number) {
    width: 100% !important;
  }
}
</style>
