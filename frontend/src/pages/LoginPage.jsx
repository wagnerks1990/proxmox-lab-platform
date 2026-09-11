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
  return <div className='login-wrap'><form className='login-card' onSubmit={submit}>
    <div className='login-brand'><img src='/brand/labgoblin-icon.svg' alt='' className='login-brand-mark'/><div><div className='brand-wordmark'>Lab<span>Goblin</span></div><div className='brand-subtitle'>Virtual Lab Provisioning & Management</div></div></div>
    <h2>Sign in</h2><p className='muted' id='login-help'>Access your assigned virtual labs.</p>
    <label htmlFor='login-username'>Username</label>
    <input id='login-username' className='input' autoComplete='username' aria-describedby='login-help' value={username} onChange={e=>setU(e.target.value)} />
    <label htmlFor='login-password'>Password</label>
    <input id='login-password' className='input' autoComplete='current-password' type='password' value={password} onChange={e=>setP(e.target.value)} />
    <button style={{width:'100%'}} disabled={!username || !password}>Sign in</button>
    <div className='login-tagline'>Real Skills. Virtual Machines.</div>
  </form></div>
}
