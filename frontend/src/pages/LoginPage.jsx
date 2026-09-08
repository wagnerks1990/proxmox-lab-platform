import { useState } from 'react'
import api from '../services/api'

export default function LoginPage({ onLogin, setMessage }) {
  const [username, setU] = useState('')
  const [password, setP] = useState('')
  const submit = async (e) => {
    e.preventDefault()
    try {
      await api.post('/auth/login', { username, password })
      setMessage({ type: 'success', text: 'Welcome back. Login successful.' })
      onLogin()
    } catch (error) {
      setMessage({ type: 'error', text: error?.response?.data?.detail || 'Login failed. Check credentials.' })
    }
  }
  return <div className='login-wrap'><form className='login-card' onSubmit={submit}><h2>Lab Login</h2><p style={{color:'#a7b0d6'}}>Access your assigned Proxmox labs.</p><input className='input' autoComplete='username' value={username} onChange={e=>setU(e.target.value)} placeholder='Username' /><input className='input' autoComplete='current-password' type='password' value={password} onChange={e=>setP(e.target.value)} placeholder='Password' /><button style={{width:'100%'}} disabled={!username || !password}>Sign in</button></form></div>
}
