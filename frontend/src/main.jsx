import React from 'react'
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
import PlaceholderAdminPage from './pages/PlaceholderAdminPage'
import './styles.css'

function App() {
  const { user, setUser, loading, refresh } = useAuth()
  const [message, setMessage] = React.useState(null)
  if (loading) return <div className='login-wrap'>Loading...</div>
  if (user === false) return <><MessageBanner message={message} /><LoginPage onLogin={refresh} setMessage={setMessage} /></>
  return <BrowserRouter><AppLayout setUser={setUser} user={user}><MessageBanner message={message} /><Routes><Route path='/' element={<DashboardPage user={user} />} /><Route path='/vms' element={<VmsPage setMessage={setMessage} user={user} />} /><Route path='/create' element={<CreateVmPage setMessage={setMessage} />} /><Route path='/sessions' element={<SessionActivityPage setMessage={setMessage} />} />
          <Route path='/templates' element={<PlaceholderAdminPage title='Templates' subtitle='Visual template/image management shell.' />} />
          <Route path='/pools' element={<PlaceholderAdminPage title='Pools' subtitle='Pool management shell with assignment status.' />} />
          <Route path='/users' element={<PlaceholderAdminPage title='Users' subtitle='User/account management shell.' />} />
          <Route path='/monitoring' element={<PlaceholderAdminPage title='Monitoring' subtitle='Platform monitor and event visibility shell.' />} />
          <Route path='/settings' element={<PlaceholderAdminPage title='Settings' subtitle='Global platform settings shell.' />} /><Route path='*' element={<Navigate to='/' />} /></Routes></AppLayout></BrowserRouter>
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
