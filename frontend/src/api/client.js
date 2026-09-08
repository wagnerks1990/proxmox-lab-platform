import axios from 'axios'
const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || '/api', withCredentials: true })
api.interceptors.request.use((config) => {
  const organizationId = localStorage.getItem('organization_id')
  if (organizationId) config.headers['X-Organization-ID'] = organizationId
  return config
})
export default api
