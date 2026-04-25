import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import {
  exploreAuthApi,
  exploreAdapterApi,
  exploreTrainingDataApi,
  localExploreApi
} from '@/api/explore'

const TOKEN_KEY = 'explore_token'
const TOKEN_EXPIRE_KEY = 'explore_token_expire_at'

export const useExploreStore = defineStore('explore', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY))
  const tokenExpireAt = ref(localStorage.getItem(TOKEN_EXPIRE_KEY))
  const user = ref(null)
  const adapters = ref([])
  const trainingData = ref([])
  const loading = ref(false)
  const currentAdapter = ref(null)
  const currentTrainingData = ref(null)

  const isLoggedIn = computed(() => {
    if (!token.value) return false
    if (tokenExpireAt.value) {
      const expireTime = new Date(tokenExpireAt.value).getTime()
      if (Date.now() > expireTime) {
        logout()
        return false
      }
    }
    return true
  })

  const displayName = computed(() => user.value?.username || '')

  function setToken(newToken, expiresInSeconds = 86400) {
    token.value = newToken
    const expireAt = new Date(Date.now() + expiresInSeconds * 1000)
    tokenExpireAt.value = expireAt.toISOString()
    localStorage.setItem(TOKEN_KEY, newToken)
    localStorage.setItem(TOKEN_EXPIRE_KEY, expireAt.toISOString())
  }

  function logout() {
    token.value = null
    tokenExpireAt.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(TOKEN_EXPIRE_KEY)
  }

  async function login(credentials) {
    loading.value = true
    try {
      const res = await exploreAuthApi.login(credentials)
      if (res.data?.access_token) {
        setToken(res.data.access_token, res.data.expires_in)
        await fetchUser()
        ElMessage.success('登录成功')
        return true
      }
      throw new Error('登录失败')
    } catch (error) {
      ElMessage.error(error.message || '登录失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function register(data) {
    loading.value = true
    try {
      const res = await exploreAuthApi.register(data)
      if (res.data?.access_token) {
        setToken(res.data.access_token, res.data.expires_in)
        await fetchUser()
        ElMessage.success('注册成功')
        return true
      }
      throw new Error('注册失败')
    } catch (error) {
      ElMessage.error(error.message || '注册失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      const res = await exploreAuthApi.me()
      if (res.data) {
        user.value = res.data
      }
    } catch {
      user.value = null
    }
  }

  async function fetchAdapters(params = {}) {
    loading.value = true
    try {
      const res = await exploreAdapterApi.list(params)
      adapters.value = res.data?.items || []
      return res.data
    } catch (error) {
      ElMessage.error('获取Adapter列表失败: ' + error.message)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function fetchTrainingData(params = {}) {
    loading.value = true
    try {
      const res = await exploreTrainingDataApi.list(params)
      trainingData.value = res.data?.items || []
      return res.data
    } catch (error) {
      ElMessage.error('获取训练数据列表失败: ' + error.message)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function uploadAdapter(formData) {
    loading.value = true
    try {
      const res = await exploreAdapterApi.create(formData)
      ElMessage.success('Adapter上传成功')
      return res.data
    } catch (error) {
      ElMessage.error('上传失败: ' + error.message)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function uploadTrainingData(formData) {
    loading.value = true
    try {
      const res = await exploreTrainingDataApi.create(formData)
      ElMessage.success('训练数据上传成功')
      return res.data
    } catch (error) {
      ElMessage.error('上传失败: ' + error.message)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function uploadAdapterToCloud({ styleId, description }) {
    loading.value = true
    try {
      const res = await localExploreApi.uploadToCloud(styleId, description, token.value)
      ElMessage.success('Adapter上传成功')
      return res.data
    } catch (error) {
      const msg = error.response?.data?.detail || error.message || '上传失败'
      ElMessage.error('上传失败: ' + msg)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function pullAdapterToLocal(cloudAdapter) {
    loading.value = true
    // console.log(cloudAdapter)
    try {
      const payload = {
        cloud_adapter_id: cloudAdapter.id,
        style_name: cloudAdapter.style_name,
        style_tag: cloudAdapter.style_tag,
        description: cloudAdapter.description,
        base_model: cloudAdapter.base_model,
      }
      if (cloudAdapter.evaluation_results) {
        payload.evaluation_results = cloudAdapter.evaluation_results
      }
      // console.log(payload)
      const res = await localExploreApi.pullAdapter(payload)
      ElMessage.success('Adapter已拉取到本地')
      return res.data
    } catch (error) {
      const msg = error.response?.data?.detail || error.message || '拉取失败'
      ElMessage.error('拉取到本地失败: ' + msg)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function deleteAdapter(id) {
    loading.value = true
    try {
      await exploreAdapterApi.delete(id)
      ElMessage.success('Adapter已移除')
    } catch (error) {
      ElMessage.error('移除失败: ' + error.message)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function updateAdapter(id, data) {
    loading.value = true
    try {
      await exploreAdapterApi.update(id, data)
      ElMessage.success('Adapter信息已更新')
    } catch (error) {
      ElMessage.error('更新失败: ' + error.message)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function deleteTrainingData(id) {
    loading.value = true
    try {
      await exploreTrainingDataApi.delete(id)
      ElMessage.success('训练数据已移除')
    } catch (error) {
      ElMessage.error('移除失败: ' + error.message)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function updateTrainingData(id, data) {
    loading.value = true
    try {
      await exploreTrainingDataApi.update(id, data)
      ElMessage.success('训练数据信息已更新')
    } catch (error) {
      ElMessage.error('更新失败: ' + error.message)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function previewTrainingData(id, lineCount = 50) {
    try {
      const res = await exploreTrainingDataApi.preview(id, lineCount)
      return res.data
    } catch (error) {
      ElMessage.error('预览失败: ' + error.message)
      throw error
    }
  }

  function downloadTrainingData(item) {
    const url = exploreTrainingDataApi.downloadUrl(item.id)
    const a = document.createElement('a')
    a.href = url
    a.download = item.file_name
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  return {
    token,
    user,
    adapters,
    trainingData,
    loading,
    currentAdapter,
    currentTrainingData,
    isLoggedIn,
    displayName,
    login,
    register,
    logout,
    fetchUser,
    fetchAdapters,
    fetchTrainingData,
    uploadAdapter,
    uploadTrainingData,
    uploadAdapterToCloud,
    pullAdapterToLocal,
    deleteAdapter,
    updateAdapter,
    deleteTrainingData,
    updateTrainingData,
    previewTrainingData,
    downloadTrainingData,
    setToken,
  }
})
