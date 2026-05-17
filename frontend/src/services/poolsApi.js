import api from './api'
export const listPools = () => api.get('/pools').then(r => r.data.data)
export const getPool = (id) => api.get(`/pools/${id}`).then(r => r.data.data)
export const planPool = (id) => api.post(`/pools/${id}/plan`).then(r => r.data.data)
