import client from './client'

export const modelApi = {
  // List available base models
  list() {
    return client.get('/api/models')
  },
}

export const styleApi = {
  // List styles with pagination and search
  list(params = {}) {
    return client.get('/api/styles', { params })
  },

  // Get style by ID
  get(id) {
    return client.get(`/api/styles/${id}`)
  },

  // Create new style
  create(data) {
    return client.post('/api/styles', data)
  },

  // Update style
  update(id, data) {
    return client.put(`/api/styles/${id}`, data)
  },

  // Delete style
  delete(id) {
    return client.delete(`/api/styles/${id}`)
  },

  // Get messages for a style
  getMessages(styleId, params = {}) {
    return client.get(`/api/styles/${styleId}/messages`, { params })
  },

  // Send message (style transfer)
  sendMessage(styleId, data) {
    return client.post(`/api/styles/${styleId}/messages`, data)
  },

  // Clear messages
  clearMessages(styleId) {
    return client.delete(`/api/styles/${styleId}/messages`)
  },

  // Delete single message
  deleteMessage(styleId, messageId) {
    return client.delete(`/api/styles/${styleId}/messages/${messageId}`)
  }
}
