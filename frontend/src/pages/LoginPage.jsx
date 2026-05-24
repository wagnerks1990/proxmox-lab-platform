import { useState } from 'react'
import api from '../services/api'

export default function LoginPage({ onLogin, setMessage }) {
  const [username, setU] = useState('admin')
  const [password, setP] = useState('admin')
  const submit = async (e) => {
    e.preventDefault()
    try {
      const { data } = await api.post('/auth/login', { username, password })
      localStorage.setItem('token', data.access_token)
      setMessage({ type: 'success', text: 'Welcome back. Login successful.' })
      onLogin()
    } catch {
      setMessage({ type: 'error', text: 'Login failed. Check credentials.' })
    }
  }
  return <div className='login-wrap'><form className='login-card' onSubmit={submit}><h2>Lab Login</h2><p style={{color:'#a7b0d6'}}>Access your assigned Proxmox labs.</p><p style={{color:'#a7b0d6'}}>Development login: admin / admin</p><input className='input' value={username} onChange={e=>setU(e.target.value)} placeholder='Username' /><input className='input' type='password' value={password} onChange={e=>setP(e.target.value)} placeholder='Password' /><button style={{width:'100%'}}>Sign in</button></form></div>
}
