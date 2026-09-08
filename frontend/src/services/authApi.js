import api from './api'

export const changePassword = (payload) => api.post('/auth/change-password', payload).then(r => r.data)
export const logoutSession = () => api.post('/auth/logout')
export const listSessions = () => api.get('/auth/sessions').then(r => r.data)
export const revokeSession = (id) => api.delete(`/auth/sessions/${id}`)

