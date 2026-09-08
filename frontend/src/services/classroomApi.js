import api from './api'

const data = response => response.data?.data ?? response.data

export const listClasses = () => api.get('/admin/classes').then(data)
export const createClass = payload => api.post('/admin/classes', payload).then(data)
export const listEnrollments = classId => api.get(`/admin/classes/${classId}/enrollments`).then(data)
export const addEnrollment = (classId, payload) => api.post(`/admin/classes/${classId}/enrollments`, payload).then(data)
export const removeEnrollment = (classId, userId) => api.delete(`/admin/classes/${classId}/enrollments/${userId}`).then(data)
export const listLabs = () => api.get('/admin/labs').then(data)
export const createLab = payload => api.post('/admin/labs', payload).then(data)
export const listLabRuns = () => api.get('/admin/lab-runs').then(data)
export const createLabRun = payload => api.post('/admin/lab-runs', payload).then(data)
export const changeLabRunState = (id, action) => api.patch(`/admin/lab-runs/${id}/state`, { action }).then(data)
export const listRunAssignments = id => api.get(`/admin/lab-runs/${id}/assignments`).then(data)
export const bulkAssignRun = (id, slotsPerStudent = 1) => api.post(`/admin/lab-runs/${id}/assignments/bulk`, { slots_per_student: slotsPerStudent }).then(data)
export const revokeRunAssignment = (runId, assignmentId) => api.delete(`/admin/lab-runs/${runId}/assignments/${assignmentId}`).then(data)
export const listMyAssignments = () => api.get('/classroom/assignments').then(data)

