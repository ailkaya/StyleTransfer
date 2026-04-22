import client from './client'

export const monitoringApi = {
  getStats() {
    return client.get('/api/system/stats')
  }
}
