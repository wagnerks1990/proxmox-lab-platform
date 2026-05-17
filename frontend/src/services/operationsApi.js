import api from './api'
export const getOperationsHealth = () => api.get('/admin/operations/health').then(r => r.data.data)
