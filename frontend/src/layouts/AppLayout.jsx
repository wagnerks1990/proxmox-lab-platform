import { Link, useLocation, useNavigate } from 'react-router-dom'

export default function AppLayout({ children, setUser }) {
  const nav = useNavigate()
  const loc = useLocation()
  const logout = () => { localStorage.removeItem('token'); setUser(false); nav('/') }
  return <div className='app-shell'>
    <aside className='sidebar'>
      <div className='brand'>Proxmox Lab Portal</div>
      <Link className='nav-link' to='/'>Dashboard</Link>
      <Link className='nav-link' to='/vms'>My VMs</Link>
      <Link className='nav-link' to='/create'>Create VM</Link>
      <button onClick={logout} style={{marginTop: 10, width: '100%'}}>Logout</button>
      <div style={{marginTop:14, color:'#a7b0d6', fontSize:12}}>Current: {loc.pathname}</div>
    </aside>
    <main className='content'>{children}</main>
  </div>
}
