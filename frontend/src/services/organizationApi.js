import api from '../api/client'

export const listOrganizations = async () => (await api.get('/organizations')).data
