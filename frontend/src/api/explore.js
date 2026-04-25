import axios from 'axios'

const exploreClient = axios.create({
  baseURL: '/explore-api',
  timeout: 180000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor - add JWT token
exploreClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('explore_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    config._startTime = Date.now()
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor
exploreClient.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('explore_token')
      localStorage.removeItem('explore_token_expire_at')
    }
    const message = error.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new Error(message))
  }
)

export const exploreAuthApi = {
  register(data) {
    return exploreClient.post('/api/auth/register', data)
  },
  login(data) {
    return exploreClient.post('/api/auth/login', data)
  },
  me() {
    return exploreClient.get('/api/auth/me')
  }
}

export const exploreAdapterApi = {
  list(params = {}) {
    return exploreClient.get('/api/adapters', { params })
  },
  get(id) {
    return exploreClient.get(`/api/adapters/${id}`)
  },
  create(formData) {
    return exploreClient.post('/api/adapters', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  update(id, data) {
    return exploreClient.put(`/api/adapters/${id}`, data)
  },
  delete(id) {
    return exploreClient.delete(`/api/adapters/${id}`)
  },
  downloadUrl(id) {
    return `/explore-api/api/adapters/${id}/download`
  }
}

export const exploreTrainingDataApi = {
  list(params = {}) {
    return exploreClient.get('/api/training-data', { params })
  },
  get(id) {
    return exploreClient.get(`/api/training-data/${id}`)
  },
  create(formData) {
    return exploreClient.post('/api/training-data', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  update(id, data) {
    return exploreClient.put(`/api/training-data/${id}`, data)
  },
  delete(id) {
    return exploreClient.delete(`/api/training-data/${id}`)
  },
  preview(id, lineCount = 50) {
    return exploreClient.get(`/api/training-data/${id}/preview`, {
      params: { line_count: lineCount }
    })
  },
  downloadUrl(id) {
    return `/explore-api/api/training-data/${id}/download`
  }
}

export const localExploreApi = {
  pullAdapter(data) {
    return axios.create({ baseURL: '', timeout: 300000 }).post('/api/explore/pull-adapter', data)
  },
  uploadToCloud(styleId, description, cloudToken) {
    const client = axios.create({ baseURL: '', timeout: 300000 })
    return client.post('/api/explore/upload-to-cloud', null, {
      params: { style_id: styleId, description, cloud_token: cloudToken }
    })
  },
  listLocalStyles(params = {}) {
    return axios.create({ baseURL: '', timeout: 30000 }).get('/api/styles', { params })
  }
}
