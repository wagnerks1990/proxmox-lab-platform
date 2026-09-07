import api from '../api/client'

export const listAdminOrganizations = () => api.get('/admin/organizations').then(r => r.data)
export const createOrganization = payload => api.post('/admin/organizations', payload).then(r => r.data)
export const patchOrganization = (id, payload) => api.patch(`/admin/organizations/${id}`, payload).then(r => r.data)
export const listOrganizationMembers = id => api.get(`/admin/organizations/${id}/members`).then(r => r.data)
export const putOrganizationMember = (organizationId, userId, payload) => api.put(`/admin/organizations/${organizationId}/members/${userId}`, payload).then(r => r.data)
export const deactivateOrganizationMember = (organizationId, userId) => api.delete(`/admin/organizations/${organizationId}/members/${userId}`).then(r => r.data)
