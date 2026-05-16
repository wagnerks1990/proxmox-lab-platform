import { Link, useLocation } from 'react-router-dom'
import AdminOnly from './AdminOnly'

const Item = ({ to, children }) => {
  const loc = useLocation()
  const active = loc.pathname === to
  return <Link className={active ? 'nav-active' : ''} to={to}>{children}</Link>
}

export default function Sidebar({ user }) {
  const badge = (user?.role || 'student').toLowerCase()
  return <aside className='sidebar2'>
    <div className='brand2'>Proxmox Lab Manager</div>
    <div className={`role-badge ${badge}`}>{badge}</div>
    <nav>
      <Item to='/'>Dashboard</Item>
      <Item to='/vms'>My Lab VMs</Item>
      <Item to='/create'>Create Lab</Item>
      <Item to='/sessions'>Sessions</Item>
      <AdminOnly user={user}><>
        <Item to='/proxmox'>Proxmox</Item>
        <Item to='/templates'>Templates</Item>
        <Item to='/desktop-pools'>Desktop Pools</Item>
        <Item to='/pools'>Resource Pools</Item>
        <Item to='/users'>Users / Groups</Item>
        <Item to='/monitoring'>Monitoring</Item>
        <Item to='/validation'>Validation</Item>
        <Item to='/settings'>Settings</Item>
      </></AdminOnly>
    </nav>
  </aside>
}
