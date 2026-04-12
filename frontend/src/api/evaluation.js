import client from './client'

export const evaluationApi = {
  // Get evaluation report for a task
  getEvaluation(taskId) {
    return client.get(`/api/tasks/${taskId}/evaluation`)
  },

  // Submit or update comment for an evaluation
  submitComment(taskId, comment) {
    return client.post(`/api/tasks/${taskId}/comment`, { comment })
  },

  // Update comment (alias for submit)
  updateComment(taskId, comment) {
    return client.put(`/api/tasks/${taskId}/comment`, { comment })
  },

  // Get comment for an evaluation
  getComment(taskId) {
    return client.get(`/api/tasks/${taskId}/comment`)
  }
}
