import axios from 'axios'
import type { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

const service: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

/** Read token from persisted Pinia storage without importing the store (avoids circular deps) */
function getToken(): string {
  try {
    const stored = localStorage.getItem('nesom-user')
    return stored ? (JSON.parse(stored).token ?? '') : ''
  } catch {
    return ''
  }
}

function getRefreshToken(): string {
  try {
    const stored = localStorage.getItem('nesom-user')
    return stored ? (JSON.parse(stored).refreshToken ?? '') : ''
  } catch {
    return ''
  }
}

function clearAuth() {
  try {
    const stored = localStorage.getItem('nesom-user')
    if (stored) {
      const data = JSON.parse(stored)
      data.token = ''
      data.refreshToken = ''
      data.userInfo = null
      localStorage.setItem('nesom-user', JSON.stringify(data))
    }
  } catch {
    localStorage.removeItem('nesom-user')
  }
}

function saveNewToken(accessToken: string, refreshToken: string) {
  try {
    const stored = localStorage.getItem('nesom-user')
    const data = stored ? JSON.parse(stored) : {}
    data.token = accessToken
    data.refreshToken = refreshToken
    localStorage.setItem('nesom-user', JSON.stringify(data))
  } catch {
    // ignore
  }
}

// Track ongoing refresh to avoid multiple simultaneous refresh calls
let refreshPromise: Promise<string> | null = null

async function doRefreshToken(): Promise<string> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) throw new Error('No refresh token')

  const response = await axios.post(
    `${import.meta.env.VITE_API_BASE_URL || '/api'}/v1/auth/refresh`,
    { refresh_token: refreshToken },
  )

  const { access_token, refresh_token } = response.data?.data ?? response.data
  saveNewToken(access_token, refresh_token)
  return access_token
}

service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

service.interceptors.response.use(
  (response: AxiosResponse) => {
    const res = response.data
    // Support both { code, data } envelope and raw data responses
    if (res && typeof res === 'object' && 'code' in res) {
      if (res.code === 200 || res.code === 0) return res.data
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || '请求失败'))
    }
    // Raw response (e.g. token endpoint returns data directly)
    return res
  },
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        // Deduplicate concurrent refresh calls
        if (!refreshPromise) {
          refreshPromise = doRefreshToken().finally(() => {
            refreshPromise = null
          })
        }
        const newToken = await refreshPromise
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return service(originalRequest)
      } catch {
        clearAuth()
        ElMessage.error('登录已过期，请重新登录')
        window.location.href = '/login'
        return Promise.reject(error)
      }
    }

    if (error.response) {
      const status = error.response.status
      const messages: Record<number, string> = {
        403: '权限不足',
        404: '请求的资源不存在',
        423: '账户已被锁定',
        500: '服务器内部错误',
      }
      // Don't show generic message for 401 (handled above) or 422 (form validation)
      if (status !== 401 && status !== 422) {
        ElMessage.error(messages[status] || error.response.data?.message || '请求失败')
      }
    } else {
      ElMessage.error('网络错误，请检查网络连接')
    }

    return Promise.reject(error)
  },
)

export default service
