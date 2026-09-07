import api from '../api/client'

export const listOrganizations = async () => (await api.get('/organizations')).data
export const listCurrentOrganizationMembers = async () => (await api.get('/organization/members')).data
