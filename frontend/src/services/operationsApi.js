import api from './api'

export const getOperationsHealth = () =>
  api.get('/admin/operations/health').then((r) => r.data?.data ?? r.data)

export const listOperations = () => api.get('/operations').then((r) => r.data?.operations ?? [])
