const norm = (u) => ((u?.role || '').toLowerCase())
export default function AdminOnly({ user, children }) {
  const r = norm(user)
  if (!(r === 'admin' || r === 'teacher' || user?.role_id === 3 || user?.role_id === 2)) return null
  return children
}
