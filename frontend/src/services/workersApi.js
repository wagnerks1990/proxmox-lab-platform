import api from './api'
export const getWorkerRuns = () => api.get('/admin/workers/runs').then(r => r.data.data)
