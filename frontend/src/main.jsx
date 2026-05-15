import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import api from './api/client'

function Login({ onLogin }) {
  const [username, setU] = useState('alice')
  const [password, setP] = useState('Password123!')
  const [message, setMessage] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    try {
      const { data } = await api.post('/auth/login', { username, password })
      localStorage.setItem('token', data.access_token)
      setMessage('Login successful')
      onLogin()
    } catch (err) {
      setMessage(err?.response?.data?.detail || 'Login failed')
    }
  }

  return <form onSubmit={submit}><h2>Login</h2><input value={username} onChange={e=>setU(e.target.value)} /><input type='password' value={password} onChange={e=>setP(e.target.value)} /><button>Login</button><div>{message}</div></form>
}

function Dashboard({ user }) { return <div><h2>{user.role} Dashboard</h2><Link to='/vms'>My VMs</Link> | <Link to='/create'>Create VM</Link></div> }

function VMs() {
  const [vms,setV]=useState([])
  const [message, setMessage] = useState('')

  const load = async () => {
    try {
      const r = await api.get('/vms')
      setV(r.data)
    } catch (err) {
      setMessage(err?.response?.data?.detail?.message || err?.response?.data?.detail || 'Failed to load VMs')
    }
  }

  useEffect(()=>{load()},[])

  const action = async (vmId, fn, successText) => {
    try {
      await fn(vmId)
      setMessage(successText)
      await load()
    } catch (err) {
      const detail = err?.response?.data?.detail
      setMessage(detail?.message ? `${detail.message}: ${detail.details || ''}` : (detail || 'VM action failed'))
    }
  }

  return <div>
    <h3>My VMs</h3>
    <button onClick={load}>Refresh All</button>
    <div>{message}</div>
    <ul>{vms.map(v=><li key={v.id}>{v.vm_name} ({v.status})
      <button onClick={()=>action(v.id, (id)=>api.post(`/vms/${id}/start`), 'VM started')}>Start</button>
      <button onClick={()=>action(v.id, (id)=>api.post(`/vms/${id}/stop`), 'VM stopped')}>Stop</button>
      <button onClick={()=>action(v.id, (id)=>api.post(`/vms/${id}/reboot`), 'VM rebooted')}>Reboot</button>
      <button onClick={()=>action(v.id, (id)=>api.delete(`/vms/${id}`), 'VM deleted')}>Delete</button>
      <button onClick={()=>action(v.id, (id)=>api.get(`/vms/${id}/status`), 'Status refreshed')}>Refresh Status</button>
    </li>)}</ul>
  </div>
}

function CreateVM() {
  const [templates,setT]=useState([])
  const [templateId,setId]=useState('')
  const [labName,setL]=useState('linuxlab')
  const [message, setMessage] = useState('')
  useEffect(()=>{api.get('/templates').then(r=>{setT(r.data); if(r.data[0]) setId(r.data[0].id)}).catch(()=>setMessage('Failed to load templates'))},[])
  const create=async()=>{
    try {
      await api.post('/vms',{template_id:Number(templateId),lab_name:labName,auto_start:true})
      setMessage('VM created successfully')
    } catch (err) {
      const detail = err?.response?.data?.detail
      setMessage(detail?.message ? `${detail.message}: ${detail.details || ''}` : (detail || 'Failed to create VM'))
    }
  }
  return <div><h3>Create VM</h3><select value={templateId} onChange={e=>setId(e.target.value)}>{templates.map(t=><option value={t.id} key={t.id}>{t.name}</option>)}</select><input value={labName} onChange={e=>setL(e.target.value)} /><button onClick={create}>Create</button><div>{message}</div></div>
}

function App(){ const [user,setUser]=useState(null); const load=()=>api.get('/auth/me').then(r=>setUser(r.data)).catch(()=>setUser(false)); useEffect(()=>{load()},[]); if(user===null) return <div>Loading...</div>; if(user===false) return <Login onLogin={load}/>; return <BrowserRouter><nav><Link to='/'>Home</Link></nav><Routes><Route path='/' element={<Dashboard user={user}/>} /><Route path='/vms' element={<VMs/>} /><Route path='/create' element={<CreateVM/>} /><Route path='*' element={<Navigate to='/'/>}/></Routes></BrowserRouter> }
ReactDOM.createRoot(document.getElementById('root')).render(<App />)
