export function deriveCapabilities(user, tenantRole) {
  const platformAdmin = String(user?.role || '').toLowerCase() === 'admin'
  const role = String(tenantRole || '').toLowerCase()
  return {
    platformAdmin,
    tenantInstructor: platformAdmin || ['instructor', 'admin', 'owner'].includes(role),
    tenantAdmin: platformAdmin || ['admin', 'owner'].includes(role),
  }
}
