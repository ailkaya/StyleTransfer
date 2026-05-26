import client from './client'

export const configApi = {
  // Get all configurations grouped by category
  getConfig() {
    return client.get('/api/config')
  },

  // Update configurations (batch update)
  updateConfig(configs) {
    return client.post('/api/config', { configs })
  },

  // Get hint about which configurations require restart
  getRestartHint() {
    return client.get('/api/config/reload-hint')
  },
}
