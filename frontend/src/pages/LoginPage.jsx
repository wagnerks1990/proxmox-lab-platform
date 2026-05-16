import { useState } from 'react'
import api from '../services/api'

export default function LoginPage({ onLogin, setMessage }) {
  const [username, setU] = useState('alice')
  const [password, setP] = useState('Password123!')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      const { data } = await api.post('/auth/login', { username, password })
      if (!data?.access_token) throw new Error('No access token returned')
      localStorage.setItem('token', data.access_token)
      console.log('[auth] login:token-saved', { hasToken: true })
      await onLogin()
      setMessage({ type: 'success', text: 'Welcome back. Login successful.' })
    } catch (err) {
      console.error('[auth] login:failed', err?.response?.status, err?.response?.data || err)
      setMessage({ type: 'error', text: err?.response?.data?.detail || 'Login failed. Check credentials.' })
    } finally {
      setBusy(false)
    }
  }

  return <div className='login-wrap'><form className='login-card' onSubmit={submit}><h2>Lab Login</h2><p style={{color:'#a7b0d6'}}>Access your assigned Proxmox labs.</p><input className='input' value={username} onChange={e=>setU(e.target.value)} placeholder='Username' /><input className='input' type='password' value={password} onChange={e=>setP(e.target.value)} placeholder='Password' /><button style={{width:'100%'}} disabled={busy}>{busy ? 'Signing in...' : 'Sign in'}</button></form></div>
}
