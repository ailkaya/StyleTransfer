import client from './client'

export const taskApi = {
  // List tasks with pagination and filters
  list(params = {}) {
    return client.get('/api/tasks', { params })
  },

  // Get latest task by style ID (returns full task details)
  getByStyleId(styleId) {
    return client.get('/api/tasks', { params: { style_id: styleId, page_size: 1 } })
  },

  // Get full task details by ID
  getFullTask(taskId) {
    return client.get(`/api/tasks/${taskId}`)
  },

  // Get task by ID
  get(id) {
    return client.get(`/api/tasks/${id}`)
  },

  // Create new training task
  create(data) {
    return client.post('/api/tasks', data)
  },

  // Get task logs
  getLogs(id, params = {}) {
    return client.get(`/api/tasks/${id}/logs`, { params })
  }
}
