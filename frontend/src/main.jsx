import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import api from './api/client'

function Login({ onLogin, setMessage }) {
  const [username, setU] = useState('alice')
  const [password, setP] = useState('Password123!')
  const submit = async (e) => {
    e.preventDefault()
    try {
      const { data } = await api.post('/auth/login', { username, password })
      localStorage.setItem('token', data.access_token)
      setMessage({ type: 'success', text: 'Login successful.' })
      onLogin()
    } catch (err) {
      setMessage({ type: 'error', text: err?.response?.data?.detail || 'Login failed.' })
    }
  }
  return <form onSubmit={submit}><h2>Login</h2><input value={username} onChange={e=>setU(e.target.value)} /><input type='password' value={password} onChange={e=>setP(e.target.value)} /><button>Login</button></form>
}

function Dashboard({ user }) { return <div><h2>{user.role} Dashboard</h2><Link to='/vms'>My VMs</Link> | <Link to='/create'>Create VM</Link></div> }

function VMs({ setMessage }) {
  const [vms, setV] = useState([])
  const load = async () => { const r = await api.get('/vms'); setV(r.data) }
  useEffect(() => { load() }, [])
  const run = async (id, action) => {
    try {
      if (action === 'delete') await api.delete(`/vms/${id}`)
      else if (action === 'status') await api.get(`/vms/${id}/status`)
      else await api.post(`/vms/${id}/${action}`)
      setMessage({ type: 'success', text: `VM ${action} successful.` })
      await load()
    } catch (err) {
      setMessage({ type: 'error', text: JSON.stringify(err?.response?.data?.detail || `VM ${action} failed.`) })
    }
  }
  return <div><h3>My VMs</h3><table><thead><tr><th>Name</th><th>VMID</th><th>Status</th><th>Node</th><th>Actions</th></tr></thead><tbody>{vms.map(v=><tr key={v.id}><td>{v.vm_name}</td><td>{v.vmid}</td><td>{v.status}</td><td>{v.proxmox_node}</td><td><button onClick={()=>run(v.id,'start')}>Start</button><button onClick={()=>run(v.id,'stop')}>Stop</button><button onClick={()=>run(v.id,'reboot')}>Reboot</button><button onClick={()=>run(v.id,'delete')}>Delete</button><button onClick={()=>run(v.id,'status')}>Refresh Status</button></td></tr>)}</tbody></table></div>
}

function CreateVM({ setMessage }) { const [templates,setT]=useState([]); const [templateId,setId]=useState(''); const [labName,setL]=useState('linuxlab'); useEffect(()=>{api.get('/templates').then(r=>{setT(r.data); if(r.data[0]) setId(r.data[0].id)})},[]); const create=async()=>{try{await api.post('/vms',{template_id:Number(templateId),lab_name:labName,auto_start:true}); setMessage({type:'success',text:'VM created successfully.'});}catch(err){setMessage({type:'error',text:JSON.stringify(err?.response?.data?.detail||'Create VM failed.')});}}; return <div><h3>Create VM</h3><select value={templateId} onChange={e=>setId(e.target.value)}>{templates.map(t=><option value={t.id} key={t.id}>{t.name}</option>)}</select><input value={labName} onChange={e=>setL(e.target.value)} /><button onClick={create}>Create</button></div> }

function App(){ const [user,setUser]=useState(null); const [message,setMessage]=useState(null); const load=()=>api.get('/auth/me').then(r=>setUser(r.data)).catch(()=>setUser(false)); useEffect(()=>{load()},[]); if(user===null) return <div>Loading...</div>; if(user===false) return <><Message message={message}/><Login onLogin={load} setMessage={setMessage}/></>; return <BrowserRouter><nav><Link to='/'>Home</Link></nav><Message message={message}/><Routes><Route path='/' element={<Dashboard user={user}/>} /><Route path='/vms' element={<VMs setMessage={setMessage}/>} /><Route path='/create' element={<CreateVM setMessage={setMessage}/>} /><Route path='*' element={<Navigate to='/'/>}/></Routes></BrowserRouter> }

function Message({ message }) { if (!message) return null; return <div style={{color: message.type === 'error' ? 'red' : 'green'}}>{message.text}</div> }
ReactDOM.createRoot(document.getElementById('root')).render(<App />)
