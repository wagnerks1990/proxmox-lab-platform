import axios from 'axios'
const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || '/api', withCredentials: true })
api.interceptors.request.use((config) => {
  const organizationId = localStorage.getItem('organization_id')
  if (organizationId) config.headers['X-Organization-ID'] = organizationId
  return config
})
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      window.dispatchEvent(new CustomEvent('auth:unauthorized'))
    }
    return Promise.reject(error)
  },
)
export default api
