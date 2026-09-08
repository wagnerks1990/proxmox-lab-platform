import React, { useEffect, useMemo, useRef, useState } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import useAuth from './hooks/useAuth'
import MessageBanner from './components/MessageBanner'
import AppLayout from './layouts/AppLayout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import VmsPage from './pages/VmsPage'
import CreateVmPage from './pages/CreateVmPage'
import SessionActivityPage from './pages/SessionActivityPage'
import TelemetryPage from './pages/TelemetryPage'
import PoolsPage from './pages/PoolsPage'
import PoolDetailPage from './pages/PoolDetailPage'
import OperationsPage from './pages/OperationsPage'
import TroubleshootingPage from './pages/TroubleshootingPage'
import ProxmoxSetupPage from './pages/ProxmoxSetupPage'
import ProxmoxInventoryPage from './pages/ProxmoxInventoryPage'
import ProxmoxAssetsPage from './pages/ProxmoxAssetsPage'
import UsersPage from './pages/UsersPage'
import GroupsPage from './pages/GroupsPage'
import EventsPage from './pages/EventsPage'
import SystemUpdatePage from './pages/SystemUpdatePage'
import OrganizationsPage from './pages/OrganizationsPage'
import AccountSecurityPage from './pages/AccountSecurityPage'
import ClassroomPage from './pages/ClassroomPage'
import BootstrapPage from './pages/BootstrapPage'
import './styles.css'
import api from './services/api'

const ConsolePage = React.lazy(() => import('./pages/ConsolePage'))
const TerminalPage = React.lazy(() => import('./pages/TerminalPage'))

function App() {
  const { user, setUser, loading, refresh } = useAuth()
  const [message, setMessage] = React.useState(null)
  const [bootstrapRequired, setBootstrapRequired] = React.useState(null)
  React.useEffect(() => {
    api.get('/bootstrap/status').then(response => setBootstrapRequired(response.data.bootstrap_required)).catch(() => setBootstrapRequired(false))
  }, [user])
  if (loading || bootstrapRequired === null) return <div className='login-wrap'>Loading...</div>
  if (bootstrapRequired) return <><MessageBanner message={message} /><BootstrapPage onComplete={refresh} setMessage={setMessage} /></>
  if (user === false) return <><MessageBanner message={message} /><LoginPage onLogin={refresh} setMessage={setMessage} /></>
  if (user.force_password_change) return <><MessageBanner message={message} /><div className='login-wrap'><div className='login-card' style={{width: 640}}><AccountSecurityPage forceChange onChanged={refresh} setMessage={setMessage} /></div></div></>
  return <BrowserRouter><AppLayout setUser={setUser} user={user}><MessageBanner message={message} /><Routes><Route path='/' element={<DashboardPage user={user} />} /><Route path='/account/security' element={<AccountSecurityPage onChanged={refresh} setMessage={setMessage} />} /><Route path='/classroom' element={<ClassroomPage setMessage={setMessage} />} /><Route path='/vms' element={<VmsPage setMessage={setMessage} />} /><Route path='/console/:id' element={<React.Suspense fallback={<div className='panel'>Loading console…</div>}><ConsolePage /></React.Suspense>} /><Route path='/terminal/:id' element={<React.Suspense fallback={<div className='panel'>Loading terminal…</div>}><TerminalPage /></React.Suspense>} /><Route path='/create' element={<CreateVmPage setMessage={setMessage} />} /><Route path='/admin/sessions' element={<SessionActivityPage setMessage={setMessage} />} /><Route path='/telemetry' element={<TelemetryPage />} /><Route path='/events' element={<EventsPage />} /><Route path='/pools' element={<PoolsPage />} /><Route path='/pools/:id' element={<PoolDetailPage />} /><Route path='/operations' element={<OperationsPage />} /><Route path='/troubleshooting' element={<TroubleshootingPage />} /><Route path='/admin/proxmox-setup' element={<ProxmoxSetupPage />} /><Route path='/admin/proxmox-inventory' element={<ProxmoxInventoryPage />} /><Route path='/admin/proxmox-assets' element={<ProxmoxAssetsPage />} /><Route path='/admin/users' element={<UsersPage />} /><Route path='/admin/groups' element={<GroupsPage />} /><Route path='/admin/organizations' element={<OrganizationsPage />} /><Route path='/admin/system-update' element={<SystemUpdatePage setMessage={setMessage} />} /><Route path='*' element={<Navigate to='/' />} /></Routes></AppLayout></BrowserRouter>
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
