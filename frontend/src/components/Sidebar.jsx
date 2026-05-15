import { Link } from 'react-router-dom'
import AdminOnly from './AdminOnly'

export default function Sidebar({ user }) {
  return <aside className='sidebar2'>
    <div className='brand2'>Proxmox Lab Manager</div>
    <nav>
      <Link to='/'>Dashboard</Link>
      <Link to='/vms'>My Lab VMs</Link>
      <Link to='/create'>Create Lab</Link>
      <Link to='/sessions'>Sessions</Link>
      <AdminOnly user={user}><>
        <Link to='/proxmox'>Proxmox</Link>
        <Link to='/templates'>Templates</Link>
        <Link to='/pools'>Resource Pools</Link>
        <Link to='/users'>Users</Link>
        <Link to='/monitoring'>Monitoring</Link>
        <Link to='/settings'>Settings</Link>
      </></AdminOnly>
    </nav>
  </aside>
}
