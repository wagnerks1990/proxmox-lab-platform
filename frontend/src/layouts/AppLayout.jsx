import { Link, useLocation, useNavigate } from 'react-router-dom'

export default function AppLayout({ children, setUser, user }) {
  const nav = useNavigate()
  const loc = useLocation()
  const logout = () => { localStorage.removeItem('token'); setUser(false); nav('/') }
  const role = user?.role
  const normalizedRole = (role || '').toLowerCase()
  const isTeacherOrAdmin = normalizedRole === 'teacher' || normalizedRole === 'admin' || user?.role_id === 2 || user?.role_id === 3
  const isAdmin = normalizedRole === 'admin' || user?.role_id === 3
  return <div className='app-shell'>
    <aside className='sidebar'>
      <div className='brand'>Proxmox Lab Control Plane</div>
      <Link className='nav-link' to='/'>Dashboard</Link>
      <Link className='nav-link' to='/vms'>My Lab VMs</Link>
      {isTeacherOrAdmin && <><Link className='nav-link' to='/admin/sessions'>Sessions</Link><Link className='nav-link' to='/pools'>Pools</Link><Link className='nav-link' to='/telemetry'>Telemetry</Link><Link className='nav-link' to='/operations'>Operations</Link><Link className='nav-link' to='/troubleshooting'>Troubleshooting</Link></>}
      {isAdmin && <Link className='nav-link' to='/create'>Create VM</Link>}
      <button onClick={logout} style={{marginTop: 10, width: '100%'}}>Logout</button>
      <div style={{marginTop:14, color:'#a7b0d6', fontSize:12}}>Current: {loc.pathname}</div>
    </aside>
    <main className='content'>{children}</main>
  </div>
}
