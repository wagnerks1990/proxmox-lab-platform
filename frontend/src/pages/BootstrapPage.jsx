import { useState } from 'react'
import api from '../services/api'

export default function BootstrapPage({ onComplete, setMessage }) {
  const [form, setForm] = useState({ token: '', username: '', email: '', password: '' })
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    if (form.password !== confirm) {
      setMessage({ type: 'error', text: 'Passwords do not match.' })
      return
    }
    setBusy(true)
    try {
      await api.post('/bootstrap/admin', form)
      setMessage({ type: 'success', text: 'Administrator created. Welcome to LabGoblin.' })
      await onComplete()
    } catch (error) {
      setMessage({ type: 'error', text: error?.response?.data?.detail || 'Administrator setup failed.' })
    } finally {
      setBusy(false)
    }
  }

  return <div className='login-wrap'><form className='login-card' onSubmit={submit}>
    <div className='login-brand'><img src='/brand/labgoblin-icon.svg' alt='' className='login-brand-mark'/><div><div className='brand-wordmark'>Lab<span>Goblin</span></div><div className='brand-subtitle'>Virtual Lab Provisioning & Management</div></div></div>
    <h2>First-run setup</h2>
    <p className='muted'>Create the first LabGoblin administrator. Enter the one-time token printed by the installer.</p>
    <input className='input' type='password' autoComplete='off' value={form.token} onChange={event => setForm({...form, token: event.target.value})} placeholder='Bootstrap token' />
    <input className='input' autoComplete='username' value={form.username} onChange={event => setForm({...form, username: event.target.value})} placeholder='Admin username' />
    <input className='input' type='email' autoComplete='email' value={form.email} onChange={event => setForm({...form, email: event.target.value})} placeholder='Admin email' />
    <input className='input' type='password' autoComplete='new-password' value={form.password} onChange={event => setForm({...form, password: event.target.value})} placeholder='Password' />
    <input className='input' type='password' autoComplete='new-password' value={confirm} onChange={event => setConfirm(event.target.value)} placeholder='Confirm password' />
    <button style={{width:'100%'}} disabled={busy || !form.token || !form.username || !form.email || !form.password || !confirm}>{busy ? 'Creating…' : 'Create administrator'}</button>
    <div className='login-tagline'>Build. Deploy. Learn. Repeat.</div>
  </form></div>
}
