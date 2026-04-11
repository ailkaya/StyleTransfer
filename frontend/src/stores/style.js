import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { styleApi } from '@/api/styles'

export const useStyleStore = defineStore('style', () => {
  // State
  const styles = ref([])
  const currentStyle = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const availableStyles = computed(() =>
    styles.value.filter(s => s.status === 'available' || s.status === 'completed')
  )

  const getStyleById = computed(() => (id) =>
    styles.value.find(s => s.id === id)
  )

  // Actions
  async function fetchStyles(params = {}) {
    loading.value = true
    error.value = null
    try {
      const response = await styleApi.list(params)
      styles.value = response.data.items
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchStyle(id) {
    loading.value = true
    error.value = null
    try {
      const response = await styleApi.get(id)
      currentStyle.value = response.data
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createStyle(data) {
    loading.value = true
    error.value = null
    try {
      const response = await styleApi.create(data)
      styles.value.unshift(response.data)
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateStyle(id, data) {
    loading.value = true
    error.value = null
    try {
      const response = await styleApi.update(id, data)
      const index = styles.value.findIndex(s => s.id === id)
      if (index !== -1) {
        styles.value[index] = response.data
      }
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteStyle(id) {
    loading.value = true
    error.value = null
    try {
      await styleApi.delete(id)
      styles.value = styles.value.filter(s => s.id !== id)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  function setCurrentStyle(style) {
    currentStyle.value = style
  }

  return {
    styles,
    currentStyle,
    loading,
    error,
    availableStyles,
    getStyleById,
    fetchStyles,
    fetchStyle,
    createStyle,
    updateStyle,
    deleteStyle,
    setCurrentStyle
  }
})
