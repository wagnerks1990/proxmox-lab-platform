import { Link, useNavigate } from 'react-router-dom'

export default function AppLayout({ children, setUser }) {
  const nav = useNavigate()
  const logout = () => { localStorage.removeItem('token'); setUser(false); nav('/') }
  return <div style={{ maxWidth: 1200, margin: '0 auto', padding: 16 }}>
    <nav style={{ display:'flex', gap:10, alignItems:'center', marginBottom: 12 }}>
      <Link to='/'>Dashboard</Link>
      <Link to='/vms'>My VMs</Link>
      <Link to='/create'>Create VM</Link>
      <button onClick={logout}>Logout</button>
    </nav>
    {children}
  </div>
}
