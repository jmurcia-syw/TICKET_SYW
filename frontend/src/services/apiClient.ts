import axios from 'axios'
import { useAuthStore } from '../store/authStore'
import { notifyApiError } from './errorNotifier'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:5000',
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error)) {
      if (error.response?.status === 401) {
        // Sesión inválida/expirada: se conserva el flujo actual, sin toast.
        useAuthStore.getState().logout()
        window.location.href = '/login'
      } else {
        notifyApiError(error)
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient
