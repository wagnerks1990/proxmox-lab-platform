import api from './api'
export const getTroubleshootingRecent = () => api.get('/admin/troubleshooting/recent').then(r => r.data.data)
