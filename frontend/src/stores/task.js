import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { taskApi } from '@/api/tasks'

export const useTaskStore = defineStore('task', () => {
  // State
  const tasks = ref([])
  const currentTask = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const pendingTasks = computed(() =>
    tasks.value.filter(t => t.status === 'PENDING')
  )

  const runningTasks = computed(() =>
    tasks.value.filter(t => t.status === 'PROCESSING')
  )

  const completedTasks = computed(() =>
    tasks.value.filter(t => t.status === 'COMPLETED')
  )

  // Actions
  async function fetchTasks(params = {}) {
    console.log('[TaskStore] Fetching tasks with params:', params)
    loading.value = true
    error.value = null
    try {
      const response = await taskApi.list(params)
      console.log('[TaskStore] Fetched', response.data.items?.length || 0, 'tasks')
      tasks.value = response.data.items
      return response.data
    } catch (err) {
      console.error('[TaskStore] Failed to fetch tasks:', err.message)
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchTask(id) {
    console.log('[TaskStore] Fetching task:', id)
    loading.value = true
    error.value = null
    try {
      const response = await taskApi.get(id)
      console.log('[TaskStore] Fetched task:', response.data?.status)
      currentTask.value = response.data
      return response.data
    } catch (err) {
      console.error('[TaskStore] Failed to fetch task:', err.message)
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createTask(data) {
    console.log('[TaskStore] Creating task with data:', {
      style_id: data.style_id,
      base_model: data.base_model,
      training_text_length: data.training_text?.length
    })
    loading.value = true
    error.value = null
    try {
      const response = await taskApi.create(data)
      console.log('[TaskStore] Task created:', response.data?.id)
      tasks.value.unshift(response.data)
      return response.data
    } catch (err) {
      console.error('[TaskStore] Failed to create task:', err.message)
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchTaskLogs(id, params = {}) {
    console.log('[TaskStore] Fetching logs for task:', id, params)
    try {
      const response = await taskApi.getLogs(id, params)
      console.log('[TaskStore] Fetched', response.data?.lines || 0, 'log lines')
      return response.data
    } catch (err) {
      console.error('[TaskStore] Failed to fetch logs:', err.message)
      throw err
    }
  }

  async function fetchEvaluation(id) {
    console.log('[TaskStore] Fetching evaluation for task:', id)
    try {
      const response = await taskApi.getEvaluation(id)
      console.log('[TaskStore] Fetched evaluation, overall score:', response.data?.overall_score)
      return response
    } catch (err) {
      console.error('[TaskStore] Failed to fetch evaluation:', err.message)
      throw err
    }
  }

  // Update task progress in local state
  function updateTaskProgress(taskId, progressData) {
    console.log('[TaskStore] Updating task progress:', taskId, progressData)
    const index = tasks.value.findIndex(t => t.id === taskId)
    if (index !== -1) {
      tasks.value[index] = { ...tasks.value[index], ...progressData }
    }
    if (currentTask.value?.id === taskId) {
      currentTask.value = { ...currentTask.value, ...progressData }
    }
  }

  return {
    tasks,
    currentTask,
    loading,
    error,
    pendingTasks,
    runningTasks,
    completedTasks,
    fetchTasks,
    fetchTask,
    createTask,
    fetchTaskLogs,
    fetchEvaluation,
    updateTaskProgress
  }
})
