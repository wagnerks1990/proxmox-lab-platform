export default function AdminOnly({ user, children }) {
  if (!user || (user.role !== 'Admin' && user.role !== 'Teacher')) return null
  return children
}
