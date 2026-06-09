import axios from 'axios'

export const ACCESS_TOKEN_KEY = 'access_token'
export const REFRESH_TOKEN_KEY = 'refresh_token'

export function setAuthTokens(accessToken, refreshToken) {
  if (accessToken) sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  if (refreshToken) sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
}

export function clearAuthTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  sessionStorage.removeItem(ACCESS_TOKEN_KEY)
  sessionStorage.removeItem(REFRESH_TOKEN_KEY)
}

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

// Attach JWT token to every request
API.interceptors.request.use((config) => {
  const token = sessionStorage.getItem(ACCESS_TOKEN_KEY)
  config.headers = config.headers || {}
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let isRefreshing = false
let refreshSubscribers = []

function subscribeTokenRefresh(cb) {
  refreshSubscribers.push(cb)
}

function onRefreshed(token) {
  refreshSubscribers.forEach((cb) => cb(token))
  refreshSubscribers = []
}

// Auto-refresh on 401
API.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalRequest = err.config
    const isAuthRequest = originalRequest?.url?.includes('/auth/')
    const isProfileBootstrap = originalRequest?.url?.includes('/profile/me')

    if (err.response?.status === 401 && originalRequest && !originalRequest._retry && !isAuthRequest) {
      if (isRefreshing) {
        return new Promise((resolve) => {
          subscribeTokenRefresh((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            resolve(API(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      const refresh = sessionStorage.getItem(REFRESH_TOKEN_KEY)
      try {
        const payload = refresh ? { refresh_token: refresh } : null
        const { data } = await axios.post(`${API.defaults.baseURL}/auth/refresh`, payload, { withCredentials: true })
        setAuthTokens(data.access_token, data.refresh_token)
        isRefreshing = false
        onRefreshed(data.access_token)
        originalRequest.headers = originalRequest.headers || {}
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`
        return API(originalRequest)
      } catch (refreshError) {
        isRefreshing = false
        clearAuthTokens()
        if (!isProfileBootstrap) window.dispatchEvent(new CustomEvent('auth-expired'))
        return Promise.reject(refreshError)
      }
    }
    return Promise.reject(err)
  }
)

// ── Auth ──────────────────────────────────────
export const authAPI = {
  register:           (data)  => API.post('/auth/register', data),
  login:              (data)  => API.post('/auth/login', data),
  getGoogleUrl:       ()      => API.get('/auth/google/url'),
  google:             (data)  => API.post('/auth/google', data),
  github:             (data)  => API.post('/auth/github', data),
  sendOtp:            (data)  => API.post('/auth/send-otp', data),
  verifyOtp:          (data)  => API.post('/auth/verify-otp', data),
  refresh:            (token) => API.post('/auth/refresh', { refresh_token: token }),
  forgotPassword:     (email) => API.post('/auth/forgot-password', { email }),
  resetPassword:      (token, newPassword) => API.post('/auth/reset-password', { token, new_password: newPassword }),
  verifyEmail:        (token) => API.post('/auth/verify-email', { token }),
  resendVerification: (email) => API.post('/auth/resend-verification', { email }),
  logout:             ()      => API.post('/auth/logout'),
}

// ── Profile ────────────────────────────────────
export const profileAPI = {
  getMe:           ()     => API.get('/profile/me'),
  updateMe:        (data) => API.put('/profile/me', data),
  submitQuiz:      (data) => API.post('/profile/dosha-quiz', data),
  uploadAvatar:    (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return API.post('/profile/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  changePassword:  (currentPassword, newPassword) =>
    API.patch('/profile/password', { current_password: currentPassword, new_password: newPassword }),
}

// ── Plans ──────────────────────────────────────
export const plansAPI = {
  generate:           (mode = 'agentic') => API.post('/plans/generate', { mode }),
  adapt:              (feedback, previousPlanId = null, mode = 'agentic') => API.post('/plans/generate', { mode, feedback, previous_plan_id: previousPlanId }),
  getLatest:          ()      => API.get('/plans/latest'),
  getHistory:         (offset = 0, limit = 20) => API.get('/plans/history', { params: { offset, limit } }),
  rate:               (planId, data) => API.post(`/plans/${planId}/rating`, data),
  getSeasonal:        ()      => API.get('/plans/seasonal'),
  generateMeditation: (params) => API.get('/plans/meditation', { params }),
  checkInteractions:  (herbs) => API.post('/plans/interaction-check', herbs),
  getJobStatus:       (jobId) => API.get(`/plans/job/${jobId}`),
}

// ── Preferences ────────────────────────────────
export const preferencesAPI = {
  getAll:             () => API.get('/preferences'),
  getFeature:         (feature) => API.get(`/preferences/${feature}`),
  saveFeature:        (feature, data) => API.post(`/preferences/${feature}`, data),
}

// ── Chat ───────────────────────────────────────
export const chatAPI = {
  sendMessage:  (content, session_id) =>
    API.post('/chat/message', { content, session_id }),
  getSessions:  ()           => API.get('/chat/sessions'),
  getSession:   (sessionId)  => API.get(`/chat/sessions/${sessionId}`),
}

// ── Progress ───────────────────────────────────
export const progressAPI = {
  log:        (data) => API.post('/progress/log', data),
  getSummary: ()     => API.get('/progress/summary'),
}

// ── Export ─────────────────────────────────────
export const exportAPI = {
  pdf: () => API.get('/export/pdf', { responseType: 'blob' }),
  csv: () => API.get('/export/csv', { responseType: 'blob' }),
}

// ── Notifications ──────────────────────────────
export const notificationsAPI = {
  list:        (offset = 0, limit = 50) => API.get('/notifications', { params: { offset, limit } }),
  unreadCount: ()   => API.get('/notifications/unread-count'),
  markRead:    (id) => API.put(`/notifications/${id}/read`),
  markAllRead: ()   => API.post('/notifications/mark-all-read'),
}

export const remindersAPI = {
  list:   (offset = 0, limit = 50) => API.get('/reminders', { params: { offset, limit } }),
  create: (data) => API.post('/reminders', data),
  update: (id, data) => API.put(`/reminders/${id}`, data),
  remove: (id) => API.delete(`/reminders/${id}`),
}

export const privacyAPI = {
  exportData:    () => API.get('/privacy/export'),
  deleteAccount: () => API.delete('/privacy/account'),
}

export const adminAPI = {
  summary: (token) => API.get('/admin/summary', { headers: { 'X-Admin-Token': token } }),
  users:   (token) => API.get('/admin/users', { headers: { 'X-Admin-Token': token } }),
  metrics: (token) => API.get('/health/metrics', { headers: { 'X-Admin-Token': token } }),
}

// ── Community Feed ─────────────────────────────
export const communityAPI = {
  list:       (offset = 0, limit = 20) => API.get('/community', { params: { offset, limit } }),
  create:     (content) => API.post('/community', { content }),
  toggleLike: (postId) => API.post(`/community/${postId}/like`),
  remove:     (postId) => API.delete(`/community/${postId}`),
}

// ── Weather ────────────────────────────────────
export const weatherAPI = {
  getCurrent: (lat, lon) => API.get('/weather', { params: { lat, lon } }),
}

export default API
