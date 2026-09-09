const norm = (u) => ((u?.role || '').toLowerCase())
export default function AdminOnly({ user, children }) {
  const r = norm(user)
  if (!(r === 'admin' || r === 'teacher')) return null
  return children
}
