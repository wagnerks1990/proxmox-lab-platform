import api from './api'

export const listGroups = () => api.get('/admin/groups').then(r => r.data)
export const createGroup = (payload) => api.post('/admin/groups', payload).then(r => r.data)
export const patchGroup = (id, payload) => api.patch(`/admin/groups/${id}`, payload).then(r => r.data)
export const deleteGroup = (id) => api.delete(`/admin/groups/${id}`).then(r => r.data)
export const listGroupMembers = (id) => api.get(`/admin/groups/${id}/members`).then(r => r.data)
export const addGroupMember = (id, payload) => api.post(`/admin/groups/${id}/members`, payload).then(r => r.data)
export const removeGroupMember = (id, user_id) => api.delete(`/admin/groups/${id}/members/${user_id}`).then(r => r.data)
export const listGroupTemplatePermissions = (id) => api.get(`/admin/groups/${id}/template-permissions`).then(r => r.data)
export const patchGroupTemplatePermissions = (id, template_ids) => api.patch(`/admin/groups/${id}/template-permissions`, { template_ids }).then(r => r.data)
