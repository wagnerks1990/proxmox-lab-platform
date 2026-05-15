import { useState } from 'react'
import api from '../services/api'

export default function LoginPage({ onLogin, setMessage }) {
  const [username, setU] = useState('alice')
  const [password, setP] = useState('Password123!')
  const submit = async (e) => {
    e.preventDefault()
    try {
      const { data } = await api.post('/auth/login', { username, password })
      localStorage.setItem('token', data.access_token)
      setMessage({ type: 'success', text: 'Login successful' })
      onLogin()
    } catch {
      setMessage({ type: 'error', text: 'Login failed' })
    }
  }
  return <form onSubmit={submit}><h2>Login</h2><input value={username} onChange={e=>setU(e.target.value)} /><input type='password' value={password} onChange={e=>setP(e.target.value)} /><button>Login</button></form>
}
