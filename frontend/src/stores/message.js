import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { styleApi } from '@/api/styles'

export const useMessageStore = defineStore('message', () => {
  // State
  const messages = ref([])
  const loading = ref(false)
  const error = ref(null)
  const sending = ref(false)

  // Getters
  const hasMessages = computed(() => messages.value.length > 0)

  const messagesByStyle = computed(() => {
    const grouped = {}
    messages.value.forEach(msg => {
      if (!grouped[msg.style_id]) {
        grouped[msg.style_id] = []
      }
      grouped[msg.style_id].push(msg)
    })
    return grouped
  })

  // Actions
  async function fetchMessages(styleId, params = {}) {
    loading.value = true
    error.value = null
    try {
      const response = await styleApi.getMessages(styleId, params)
      if (params.page === 1 || !params.page) {
        messages.value = response.data.items
      } else {
        messages.value.push(...response.data.items)
      }
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function sendMessage(styleId, data) {
    sending.value = true
    error.value = null
    try {
      // Add user message immediately
      const userMessage = {
        id: Date.now(),
        style_id: styleId,
        role: 'user',
        content: data.requirement,
        original_text: data.original_text,
        requirement: data.requirement,
        created_at: new Date().toISOString()
      }
      messages.value.push(userMessage)

      // Call API
      const response = await styleApi.sendMessage(styleId, data)

      // Add assistant response
      messages.value.push(response.data.message)

      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      sending.value = false
    }
  }

  async function clearMessages(styleId) {
    loading.value = true
    error.value = null
    try {
      await styleApi.clearMessages(styleId)
      messages.value = messages.value.filter(m => m.style_id !== styleId)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteMessage(styleId, messageId) {
    loading.value = true
    error.value = null
    try {
      await styleApi.deleteMessage(styleId, messageId)
      messages.value = messages.value.filter(m => m.id !== messageId)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  function addMessage(message) {
    messages.value.push(message)
  }

  function clearLocalMessages() {
    messages.value = []
  }

  return {
    messages,
    loading,
    error,
    sending,
    hasMessages,
    messagesByStyle,
    fetchMessages,
    sendMessage,
    clearMessages,
    deleteMessage,
    addMessage,
    clearLocalMessages
  }
})
