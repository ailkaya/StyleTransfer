import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { taskApi } from '@/api/tasks'

export const useTaskStore = defineStore('task', () => {
  // State
  const tasks = ref([])
  const currentTask = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const wsConnection = ref(null)

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
      return response
    } catch (err) {
      console.error('[TaskStore] Failed to fetch evaluation:', err.message)
      throw err
    }
  }

  // WebSocket connection for real-time progress
  function connectToTaskProgress(taskId, onMessage) {
    const wsUrl = `ws://${window.location.host}/ws/tasks/${taskId}`
    console.log('[TaskStore] Connecting WebSocket:', wsUrl)

    const ws = new WebSocket(wsUrl)
    let messageCount = 0

    ws.onopen = () => {
      console.log('[TaskStore] WebSocket connected for task:', taskId)
    }

    ws.onmessage = (event) => {
      messageCount++
      const data = JSON.parse(event.data)
      console.log(`[TaskStore] WebSocket message #${messageCount}:`, {
        type: data.type,
        task_id: data.task_id,
        status: data.data?.status,
        progress: data.data?.progress
      })
      onMessage(data)
    }

    ws.onerror = (error) => {
      console.error('[TaskStore] WebSocket error:', error)
    }

    ws.onclose = (event) => {
      console.log('[TaskStore] WebSocket closed for task:', taskId, {
        code: event.code,
        reason: event.reason,
        messages_received: messageCount
      })
      wsConnection.value = null
    }

    wsConnection.value = ws
    return ws
  }

  function disconnectWebSocket() {
    if (wsConnection.value) {
      console.log('[TaskStore] Disconnecting WebSocket')
      wsConnection.value.close()
      wsConnection.value = null
    }
  }

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
    wsConnection,
    pendingTasks,
    runningTasks,
    completedTasks,
    fetchTasks,
    fetchTask,
    createTask,
    fetchTaskLogs,
    fetchEvaluation,
    connectToTaskProgress,
    disconnectWebSocket,
    updateTaskProgress
  }
})
