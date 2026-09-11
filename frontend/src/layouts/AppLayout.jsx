import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { listOrganizations } from '../services/organizationApi'
import { logoutSession } from '../services/authApi'
import { AccessContext } from '../components/AccessControl'
import { deriveCapabilities } from '../auth/access'

export default function AppLayout({ children, setUser, user }) {
  const nav = useNavigate()
  const loc = useLocation()
  const [organizations, setOrganizations] = useState([])
  const [organizationReady, setOrganizationReady] = useState(false)
  const [organizationError, setOrganizationError] = useState('')
  const [organizationId, setOrganizationId] = useState(localStorage.getItem('organization_id') || '')
  const [logoutError, setLogoutError] = useState('')
  const [logoutBusy, setLogoutBusy] = useState(false)
  const logout = async () => {
    setLogoutBusy(true)
    setLogoutError('')
    try {
      await logoutSession()
      localStorage.removeItem('organization_id')
      setUser(false)
      nav('/')
    } catch (error) {
      const detail = error?.response?.data?.detail
      setLogoutError(typeof detail === 'string' ? detail : 'Sign out failed. Your server session is still active; try again.')
    } finally {
      setLogoutBusy(false)
    }
  }
  useEffect(() => {
    let active = true
    listOrganizations().then((rows) => {
      if (!active) return
      const available = Array.isArray(rows) ? rows : []
      setOrganizations(available)
      const stored = localStorage.getItem('organization_id')
      const platformAdmin = String(user?.role || '').toLowerCase() === 'admin'
      const selected = available.find((item) => String(item.id) === stored) || (!platformAdmin ? available[0] : null)
      if (selected) {
        localStorage.setItem('organization_id', String(selected.id))
        setOrganizationId(String(selected.id))
      } else {
        localStorage.removeItem('organization_id')
        if (available.length === 0) setOrganizationError('No active organization membership is available for this account.')
      }
      setOrganizationReady(true)
    }).catch((error) => {
      if (!active) return
      setOrganizationError(error?.response?.data?.detail || 'Unable to load organization access.')
      setOrganizationReady(true)
    })
    return () => { active = false }
  }, [user?.role])
  const changeOrganization = (event) => {
    localStorage.setItem('organization_id', event.target.value)
    setOrganizationId(event.target.value)
    window.location.reload()
  }
  const activeOrganization = organizations.find(organization => String(organization.id) === organizationId)
  const tenantRole = activeOrganization?.role
  const access = deriveCapabilities(user, tenantRole)
  const { platformAdmin: isPlatformAdmin, tenantInstructor: isTenantInstructor, tenantAdmin: isTenantAdmin } = access
  return <div className='app-shell'>
    <aside className='sidebar'>
      <div className='brand-lockup'><img src='/brand/labgoblin-icon.svg' alt='' className='brand-mark'/><div><div className='brand-wordmark'>Lab<span>Goblin</span></div><div className='brand-subtitle'>Virtual Lab Management</div></div></div>
      {organizations.length > 0 && <label className='muted'>Organization
        <select className='input' value={organizationId} onChange={changeOrganization} style={{marginTop: 6}}>
          <option value='' disabled>Select an organization</option>
          {organizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.name}</option>)}
        </select>
      </label>}
      <Link className='nav-link' to='/'>Dashboard</Link>
      <Link className='nav-link' to='/vms'>My Lab VMs</Link>
      <Link className='nav-link' to='/create'>Create VM</Link>
      <Link className='nav-link' to='/account/security'>Account Security</Link>
      {isTenantInstructor && <><Link className='nav-link' to='/classroom'>Classroom</Link><Link className='nav-link' to='/admin/sessions'>Sessions</Link><Link className='nav-link' to='/pools'>Pools</Link><Link className='nav-link' to='/events'>Events / Tasks</Link></>}
      <Link className='nav-link' to='/operations'>Operations</Link>
      {isPlatformAdmin && <><Link className='nav-link' to='/telemetry'>Telemetry</Link><Link className='nav-link' to='/troubleshooting'>Troubleshooting</Link></>}
      {isPlatformAdmin && <Link className='nav-link' to='/admin/proxmox-setup'>Proxmox Setup</Link>}
      {isPlatformAdmin && <Link className='nav-link' to='/admin/proxmox-inventory'>Proxmox Inventory</Link>}
      {isPlatformAdmin && <Link className='nav-link' to='/admin/templates'>Templates</Link>}
      {isPlatformAdmin && <Link className='nav-link' to='/admin/proxmox-assets'>Proxmox Assets</Link>}
      {isPlatformAdmin && <Link className='nav-link' to='/admin/users'>Users</Link>}
      {isTenantAdmin && <Link className='nav-link' to='/admin/groups'>Groups</Link>}
      {isPlatformAdmin && <Link className='nav-link' to='/admin/organizations'>Organizations</Link>}
      {isPlatformAdmin && <Link className='nav-link' to='/admin/system-update'>System Updates</Link>}
      <button onClick={logout} disabled={logoutBusy} style={{marginTop: 10, width: '100%'}}>{logoutBusy ? 'Signing out…' : 'Logout'}</button>
      {logoutError ? <div className='msg error sidebar-message' role='alert'>{logoutError}</div> : null}
      <div className='brand-footer'>Real Skills. Virtual Machines.</div>
      <div style={{marginTop:8, color:'#738096', fontSize:11}}>Current: {loc.pathname}</div>
    </aside>
    <AccessContext.Provider value={access}><main className='content'>{!organizationReady ? <section className='panel'>Selecting organization…</section> : organizationError ? <section className='panel error'>{organizationError}</section> : organizations.length > 0 && !organizationId ? <section className='panel'>Select an organization to continue.</section> : children}</main></AccessContext.Provider>
  </div>
}
