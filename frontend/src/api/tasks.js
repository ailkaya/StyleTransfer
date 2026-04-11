import client from './client'

export const taskApi = {
  // List tasks with pagination and filters
  list(params = {}) {
    return client.get('/api/tasks', { params })
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
  },

  // Get evaluation HTML
  getEvaluation(id) {
    return client.get(`/api/tasks/${id}/evaluation`, {
      responseType: 'text'
    })
  }
}
