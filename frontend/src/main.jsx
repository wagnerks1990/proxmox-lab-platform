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
import './styles.css'

function App() {
  const { user, setUser, loading, refresh } = useAuth()
  const [message, setMessage] = React.useState(null)
  if (loading) return <div className='login-wrap'>Loading...</div>
  if (user === false) return <><MessageBanner message={message} /><LoginPage onLogin={refresh} setMessage={setMessage} /></>
  return <BrowserRouter><AppLayout setUser={setUser} user={user}><MessageBanner message={message} /><Routes><Route path='/' element={<DashboardPage user={user} />} /><Route path='/vms' element={<VmsPage setMessage={setMessage} />} /><Route path='/create' element={<CreateVmPage setMessage={setMessage} />} /><Route path='/admin/sessions' element={<SessionActivityPage setMessage={setMessage} />} /><Route path='/telemetry' element={<TelemetryPage />} /><Route path='/pools' element={<PoolsPage />} /><Route path='/pools/:id' element={<PoolDetailPage />} /><Route path='/operations' element={<OperationsPage />} /><Route path='/troubleshooting' element={<TroubleshootingPage />} /><Route path='*' element={<Navigate to='/' />} /></Routes></AppLayout></BrowserRouter>
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
