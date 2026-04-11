import axios from 'axios'

const client = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
client.interceptors.request.use(
  (config) => {
    const timestamp = new Date().toISOString()
    console.log(`[${timestamp}] API Request:`, {
      method: config.method?.toUpperCase(),
      url: config.url,
      data: config.data,
      params: config.params
    })
    config._startTime = Date.now()
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor
client.interceptors.response.use(
  (response) => {
    const duration = Date.now() - (response.config._startTime || Date.now())
    const timestamp = new Date().toISOString()
    console.log(`[${timestamp}] API Response (${duration}ms):`, {
      method: response.config.method?.toUpperCase(),
      url: response.config.url,
      status: response.status,
      code: response.data?.code,
      message: response.data?.message
    })
    return response.data
  },
  (error) => {
    const duration = Date.now() - (error.config?._startTime || Date.now())
    const timestamp = new Date().toISOString()
    const message = error.response?.data?.detail || error.message || '请求失败'
    console.error(`[${timestamp}] API Error (${duration}ms):`, {
      method: error.config?.method?.toUpperCase(),
      url: error.config?.url,
      status: error.response?.status,
      message: message
    })
    return Promise.reject(new Error(message))
  }
)

export default client
