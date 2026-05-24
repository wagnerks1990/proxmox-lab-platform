import api from './api'

export async function getEvents(params = {}) {
  const { data } = await api.get('/admin/events', { params })
  return data
}

