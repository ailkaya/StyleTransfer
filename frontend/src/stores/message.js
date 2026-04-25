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
        content: data.input,
        created_at: new Date().toISOString()
      }

      // Build history from previous messages
      const history = messages.value
        .filter(m => m.style_id === styleId)
        .map(m => ({
          role: m.role,
          content: m.content
        }))

      messages.value.push(userMessage)
      // console.log('History:', history)

      // Call API with history
      const response = await styleApi.sendMessage(styleId, {
        input: data.input,
        history: history.length > 0 ? history : undefined
      })
      
      // Update temp user message with real UUID from server
      const tempIndex = messages.value.findIndex(m => m.id === userMessage.id)
      if (tempIndex !== -1 && response.data.user_message) {
        messages.value[tempIndex] = response.data.user_message
      }

      // Add assistant response
      messages.value.push(response.data.message)
      // console.log('Response:', response.data)
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
      // Check if messageId is a valid UUID format
      const isValidUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(messageId)

      if (isValidUUID) {
        // Only call API for server-side messages
        await styleApi.deleteMessage(styleId, messageId)
      }
      // Remove from local store (works for both temp and server messages)
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
