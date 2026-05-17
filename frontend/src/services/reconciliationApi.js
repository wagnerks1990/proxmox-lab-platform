import api from './api'
export const getReconciliationSummary = () => api.get('/admin/reconciliation/summary').then(r => r.data.data)
export const getReconciliationPreview = () => api.post('/admin/reconciliation/preview').then(r => r.data.data)
