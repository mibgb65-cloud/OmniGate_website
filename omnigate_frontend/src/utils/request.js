import axios from 'axios'
import { ElMessage } from 'element-plus'

import router from '@/router'
import pinia from '@/stores'
import { useAuthStore } from '@/stores/auth'

const SUCCESS_CODE = 200

function normalizeApiBaseURL(value) {
  const rawValue = String(value || '').trim()
  if (!rawValue) {
    return ''
  }

  if (/^https?:\/\//i.test(rawValue)) {
    try {
      const parsedUrl = new URL(rawValue)
      parsedUrl.pathname = parsedUrl.pathname.replace(/\/api\/?$/, '/') || '/'
      return parsedUrl.toString().replace(/\/$/, '')
    } catch {
      return rawValue
    }
  }

  const normalizedValue = rawValue.replace(/\/api\/?$/, '')
  return normalizedValue === '/' ? '' : normalizedValue
}

const baseURL = normalizeApiBaseURL(import.meta.env.VITE_API_BASE_URL)

const service = axios.create({
  baseURL,
  timeout: 20000,
})

const refreshService = axios.create({
  baseURL,
  timeout: 20000,
})

let isRefreshing = false
const pendingQueue = []

function getAuthStore() {
  return useAuthStore(pinia)
}

function enqueueRequest(resolve, reject) {
  pendingQueue.push({ resolve, reject })
}

function flushQueue(error, token) {
  while (pendingQueue.length) {
    const requestTask = pendingQueue.shift()
    if (!requestTask) {
      continue
    }
    if (error) {
      requestTask.reject(error)
      continue
    }
    requestTask.resolve(token)
  }
}

async function forceLogout(message) {
  const authStore = getAuthStore()
  authStore.clearAuth()

  if (router.currentRoute.value.path !== '/login') {
    await router.replace({
      path: '/login',
      query: { redirect: router.currentRoute.value.fullPath },
    })
  }

  ElMessage.error(message || '登录状态已失效，请重新登录')
}

async function refreshAccessToken() {
  const authStore = getAuthStore()
  if (!authStore.refreshToken) {
    throw new Error('Refresh Token 不存在')
  }

  const response = await refreshService.post('/api/auth/refresh', {
    refreshToken: authStore.refreshToken,
  })

  const result = response?.data
  if (!result || result.code !== SUCCESS_CODE || !result.data?.accessToken) {
    const refreshError = new Error(result?.message || '刷新 Token 失败')
    refreshError.code = result?.code || 401
    throw refreshError
  }

  authStore.setTokenPayload(result.data)
  return result.data.accessToken
}

service.interceptors.request.use(
  (config) => {
    const authStore = getAuthStore()
    const nextConfig = { ...config }

    if (!nextConfig.skipAuth && authStore.accessToken) {
      nextConfig.headers = nextConfig.headers || {}
      nextConfig.headers.Authorization = `Bearer ${authStore.accessToken}`
    }

    return nextConfig
  },
  (error) => Promise.reject(error),
)

service.interceptors.response.use(
  (response) => {
    const result = response?.data
    if (!result || typeof result !== 'object' || !('code' in result)) {
      return result
    }

    if (result.code === SUCCESS_CODE) {
      return result.data
    }

    const businessError = new Error(result.message || '请求失败')
    businessError.code = result.code
    businessError.response = response

    if (!response.config?.skipErrorMessage) {
      ElMessage.error(businessError.message)
    }
    return Promise.reject(businessError)
  },
  async (error) => {
    const authStore = getAuthStore()
    const originalRequest = error.config || {}
    const status = error.response?.status
    const resultCode = error.response?.data?.code
    const errorMessage = error.response?.data?.message || error.message || '请求失败'

    const isRefreshRequest = String(originalRequest.url || '').includes('/api/auth/refresh')
    const shouldRefresh = (status === 401 || resultCode === 401) && !isRefreshRequest && !originalRequest._retry

    if (shouldRefresh) {
      if (!authStore.refreshToken) {
        await forceLogout('会话已过期，请重新登录')
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          enqueueRequest(
            (newToken) => {
              originalRequest.headers = originalRequest.headers || {}
              originalRequest.headers.Authorization = `Bearer ${newToken}`
              resolve(service(originalRequest))
            },
            (queueError) => reject(queueError),
          )
        })
      }

      originalRequest._retry = true
      isRefreshing = true
      try {
        const newToken = await refreshAccessToken()
        flushQueue(null, newToken)

        originalRequest.headers = originalRequest.headers || {}
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return service(originalRequest)
      } catch (refreshError) {
        flushQueue(refreshError, '')
        await forceLogout(refreshError.message || '登录过期，请重新登录')
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    if (!originalRequest.skipErrorMessage) {
      ElMessage.error(errorMessage)
    }

    return Promise.reject(error)
  },
)

export default service
