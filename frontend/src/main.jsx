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

function App() {
  const { user, setUser, loading, refresh } = useAuth()
  const [message, setMessage] = React.useState(null)
  if (loading) return <div>Loading...</div>
  if (user === false) return <><MessageBanner message={message} /><LoginPage onLogin={refresh} setMessage={setMessage} /></>
  return <BrowserRouter><AppLayout setUser={setUser}><MessageBanner message={message} /><Routes><Route path='/' element={<DashboardPage user={user} />} /><Route path='/vms' element={<VmsPage setMessage={setMessage} />} /><Route path='/create' element={<CreateVmPage setMessage={setMessage} />} /><Route path='*' element={<Navigate to='/' />} /></Routes></AppLayout></BrowserRouter>
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
