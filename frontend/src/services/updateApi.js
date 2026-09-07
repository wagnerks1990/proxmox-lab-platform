import api from '../api/client'

export const getUpdateStatus = () => api.get('/admin/system/update').then(r => r.data)
export const saveUpdateSettings = payload => api.patch('/admin/system/update/settings', payload).then(r => r.data)
export const checkForUpdate = () => api.post('/admin/system/update/check').then(r => r.data)
export const applyUpdate = target_ref => api.post('/admin/system/update/apply', { confirmation: 'APPLY', target_ref: target_ref || null }).then(r => r.data)
export const rollbackUpdate = () => api.post('/admin/system/update/rollback', { confirmation: 'ROLLBACK' }).then(r => r.data)
