import axios from 'axios'
import { supabase } from '@/lib/supabase'

const request = axios.create({
  baseURL: import.meta.env.VITE_BACKEND_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 15000
})

request.interceptors.request.use(async (config) => {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token

  if (token) {
    if (config.headers && typeof config.headers.set === 'function') {
      config.headers.set('Authorization', `Bearer ${token}`)
    } else {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${token}`
    }
  }

  return config
})

request.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error?.response?.data?.detail
    const message = Array.isArray(detail) ? detail.map((item) => item?.msg || String(item)).join('; ') : detail
    if (message) {
      error.message = message
    }
    return Promise.reject(error)
  }
)

export default request
export { request }
