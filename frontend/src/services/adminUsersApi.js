import api from './api'

export const listUsers = (params={}) => api.get('/admin/users', { params }).then(r => r.data)
export const createUser = (payload) => api.post('/admin/users', payload).then(r => r.data)
export const patchUser = (id, payload) => api.patch(`/admin/users/${id}`, payload).then(r => r.data)
export const patchUserPassword = (id, payload) => api.patch(`/admin/users/${id}/password`, payload).then(r => r.data)
export const patchUserActivate = (id, is_active) => api.patch(`/admin/users/${id}/activate`, { is_active }).then(r => r.data)
export const deleteUser = (id, force=false) => api.delete(`/admin/users/${id}`, { params: { force } }).then(r => r.data)
export const getUserPermissions = (id) => api.get(`/admin/users/${id}/permissions`).then(r => r.data)
export const patchUserPermissions = (id, template_ids) => api.patch(`/admin/users/${id}/permissions`, { template_ids }).then(r => r.data)
export const getUserActivity = (id) => api.get(`/admin/users/${id}/activity`).then(r => r.data)
