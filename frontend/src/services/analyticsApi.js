import api from './api'
export const getAnalyticsSummary = () => api.get('/admin/analytics/summary').then(r => r.data.data)
