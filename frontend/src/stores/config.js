import { defineStore } from 'pinia'
import { ref } from 'vue'
import { configApi } from '@/api/config'

export const useConfigStore = defineStore('config', () => {
  // State
  const llmConfig = ref({
    base_url: '',
    model_name: '',
    has_api_key: false
  })
  const loading = ref(false)
  const error = ref(null)
  const verifying = ref(false)

  // Actions
  async function fetchLLMConfig() {
    loading.value = true
    error.value = null
    try {
      const response = await configApi.getLLMConfig()
      llmConfig.value = response.data
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateLLMConfig(data) {
    loading.value = true
    error.value = null
    try {
      const response = await configApi.updateLLMConfig(data)
      llmConfig.value = {
        base_url: data.base_url,
        model_name: data.model_name,
        has_api_key: !!data.api_key
      }
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function verifyLLMConnection() {
    verifying.value = true
    error.value = null
    try {
      const response = await configApi.verifyLLM()
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      verifying.value = false
    }
  }

  return {
    llmConfig,
    loading,
    error,
    verifying,
    fetchLLMConfig,
    updateLLMConfig,
    verifyLLMConnection
  }
})
