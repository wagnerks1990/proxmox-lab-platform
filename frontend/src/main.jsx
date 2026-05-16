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
import PoolsPage from './pages/PoolsPage'
import TemplatesPage from './pages/TemplatesPage'
import UsersPage from './pages/UsersPage'
import MonitoringPage from './pages/MonitoringPage'
import SettingsPage from './pages/SettingsPage'
import ProxmoxPage from './pages/ProxmoxPage'
import DesktopPoolsPage from './pages/DesktopPoolsPage'
import './styles.css'

function App() {
  const { user, setUser, loading, refresh } = useAuth()
  const [message, setMessage] = React.useState(null)
  if (loading) return <div className='login-wrap'>Loading...</div>
  if (user === false) return <><MessageBanner message={message} /><LoginPage onLogin={refresh} setMessage={setMessage} /></>
  return <BrowserRouter><AppLayout setUser={setUser} user={user}><MessageBanner message={message} /><Routes><Route path='/' element={<DashboardPage user={user} />} /><Route path='/vms' element={<VmsPage setMessage={setMessage} user={user} />} /><Route path='/create' element={<CreateVmPage setMessage={setMessage} />} /><Route path='/sessions' element={<SessionActivityPage setMessage={setMessage} />} />
          <Route path='/proxmox' element={<ProxmoxPage setMessage={setMessage} />} />
          <Route path='/templates' element={<TemplatesPage setMessage={setMessage} />} />
          <Route path='/desktop-pools' element={<DesktopPoolsPage setMessage={setMessage} />} />
          <Route path='/pools' element={<PoolsPage setMessage={setMessage} />} />
          <Route path='/users' element={<UsersPage setMessage={setMessage} />} />
          <Route path='/monitoring' element={<MonitoringPage />} />
          <Route path='/settings' element={<SettingsPage setMessage={setMessage} />} /><Route path='*' element={<Navigate to='/' />} /></Routes></AppLayout></BrowserRouter>
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
