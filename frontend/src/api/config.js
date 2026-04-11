import client from './client'

export const configApi = {
  // Get LLM config
  getLLMConfig() {
    return client.get('/api/config/llm')
  },

  // Update LLM config
  updateLLMConfig(data) {
    return client.put('/api/config/llm', data)
  },

  // Verify LLM connection
  verifyLLM() {
    return client.post('/api/config/llm/verify')
  }
}
