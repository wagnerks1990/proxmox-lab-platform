import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { listOrganizations } from '../services/organizationApi'
import { logoutSession } from '../services/authApi'

export default function AppLayout({ children, setUser, user }) {
  const nav = useNavigate()
  const loc = useLocation()
  const [organizations, setOrganizations] = useState([])
  const [organizationReady, setOrganizationReady] = useState(false)
  const [organizationError, setOrganizationError] = useState('')
  const [organizationId, setOrganizationId] = useState(localStorage.getItem('organization_id') || '')
  const logout = async () => { try { await logoutSession() } catch {} localStorage.removeItem('organization_id'); setUser(false); nav('/') }
  useEffect(() => {
    let active = true
    listOrganizations().then((rows) => {
      if (!active) return
      const available = Array.isArray(rows) ? rows : []
      setOrganizations(available)
      const stored = localStorage.getItem('organization_id')
      const selected = available.find((item) => String(item.id) === stored) || available[0]
      if (selected) {
        localStorage.setItem('organization_id', String(selected.id))
        setOrganizationId(String(selected.id))
      } else {
        localStorage.removeItem('organization_id')
        setOrganizationError('No active organization membership is available for this account.')
      }
      setOrganizationReady(true)
    }).catch((error) => {
      if (!active) return
      setOrganizationError(error?.response?.data?.detail || 'Unable to load organization access.')
      setOrganizationReady(true)
    })
    return () => { active = false }
  }, [])
  const changeOrganization = (event) => {
    localStorage.setItem('organization_id', event.target.value)
    setOrganizationId(event.target.value)
    window.location.reload()
  }
  const role = user?.role
  const normalizedRole = (role || '').toLowerCase()
  const activeOrganization = organizations.find(organization => String(organization.id) === organizationId)
  const tenantRole = activeOrganization?.role
  const isPlatformAdmin = normalizedRole === 'admin' || user?.role_id === 3
  const isPlatformTeacher = normalizedRole === 'teacher' || user?.role_id === 2
  const isTenantInstructor = ['instructor', 'admin', 'owner'].includes(tenantRole) || isPlatformAdmin
  const isTenantAdmin = ['admin', 'owner'].includes(tenantRole) || isPlatformAdmin
  return <div className='app-shell'>
    <aside className='sidebar'>
      <div className='brand'>Proxmox Lab Control Plane</div>
      {organizations.length > 0 && <label className='muted'>Organization
        <select className='input' value={organizationId} onChange={changeOrganization} style={{marginTop: 6}}>
          {organizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.name}</option>)}
        </select>
      </label>}
      <Link className='nav-link' to='/'>Dashboard</Link>
      <Link className='nav-link' to='/vms'>My Lab VMs</Link>
      <Link className='nav-link' to='/create'>Create VM</Link>
      <Link className='nav-link' to='/account/security'>Account Security</Link>
      {isTenantInstructor && <><Link className='nav-link' to='/classroom'>Classroom</Link><Link className='nav-link' to='/admin/sessions'>Sessions</Link><Link className='nav-link' to='/pools'>Pools</Link><Link className='nav-link' to='/events'>Events / Tasks</Link></>}
      {(isPlatformTeacher || isPlatformAdmin) && <><Link className='nav-link' to='/telemetry'>Telemetry</Link><Link className='nav-link' to='/operations'>Operations</Link><Link className='nav-link' to='/troubleshooting'>Troubleshooting</Link></>}
      {isPlatformAdmin && <Link className='nav-link' to='/admin/proxmox-setup'>Proxmox Setup</Link>}
      {isPlatformAdmin && <Link className='nav-link' to='/admin/proxmox-inventory'>Proxmox Inventory</Link>}
      {isPlatformAdmin && <Link className='nav-link' to='/admin/proxmox-assets'>Proxmox Assets</Link>}
      {isPlatformAdmin && <Link className='nav-link' to='/admin/users'>Users</Link>}
      {isTenantAdmin && <Link className='nav-link' to='/admin/groups'>Groups</Link>}
      {isPlatformAdmin && <Link className='nav-link' to='/admin/organizations'>Organizations</Link>}
      {isPlatformAdmin && <Link className='nav-link' to='/admin/system-update'>System Updates</Link>}
      <button onClick={logout} style={{marginTop: 10, width: '100%'}}>Logout</button>
      <div style={{marginTop:14, color:'#a7b0d6', fontSize:12}}>Current: {loc.pathname}</div>
    </aside>
    <main className='content'>{!organizationReady ? <section className='panel'>Selecting organization…</section> : organizationError ? <section className='panel error'>{organizationError}</section> : children}</main>
  </div>
}
