import api from './api'
export const getTelemetrySummary = () => api.get('/admin/telemetry/summary').then(r => r.data.data)
export const getTelemetryEvents = () => api.get('/admin/telemetry/events').then(r => r.data.data)
