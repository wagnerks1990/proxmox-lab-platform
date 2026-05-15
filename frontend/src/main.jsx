import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import api from './api/client'

function Login({ onLogin }) {
  const [username, setU] = useState('alice')
  const [password, setP] = useState('Password123!')
  const submit = async (e) => { e.preventDefault(); const { data } = await api.post('/auth/login', { username, password }); localStorage.setItem('token', data.access_token); onLogin() }
  return <form onSubmit={submit}><h2>Login</h2><input value={username} onChange={e=>setU(e.target.value)} /><input type='password' value={password} onChange={e=>setP(e.target.value)} /><button>Login</button></form>
}

function Dashboard({ user }) { return <div><h2>{user.role} Dashboard</h2><Link to='/vms'>My VMs</Link> | <Link to='/create'>Create VM</Link></div> }
function VMs() { const [vms,setV]=useState([]); useEffect(()=>{api.get('/vms').then(r=>setV(r.data))},[]); return <ul>{vms.map(v=><li key={v.id}>{v.vm_name} ({v.status})</li>)}</ul> }
function CreateVM() { const [templates,setT]=useState([]); const [templateId,setId]=useState(''); const [labName,setL]=useState('linuxlab'); useEffect(()=>{api.get('/templates').then(r=>{setT(r.data); if(r.data[0]) setId(r.data[0].id)})},[]); const create=async()=>{await api.post('/vms',{template_id:Number(templateId),lab_name:labName,auto_start:true}); alert('VM created');}; return <div><h3>Create VM</h3><select value={templateId} onChange={e=>setId(e.target.value)}>{templates.map(t=><option value={t.id} key={t.id}>{t.name}</option>)}</select><input value={labName} onChange={e=>setL(e.target.value)} /><button onClick={create}>Create</button></div> }

function App(){ const [user,setUser]=useState(null); const load=()=>api.get('/auth/me').then(r=>setUser(r.data)).catch(()=>setUser(false)); useEffect(()=>{load()},[]); if(user===null) return <div>Loading...</div>; if(user===false) return <Login onLogin={load}/>; return <BrowserRouter><nav><Link to='/'>Home</Link></nav><Routes><Route path='/' element={<Dashboard user={user}/>} /><Route path='/vms' element={<VMs/>} /><Route path='/create' element={<CreateVM/>} /><Route path='*' element={<Navigate to='/'/>}/></Routes></BrowserRouter> }
ReactDOM.createRoot(document.getElementById('root')).render(<App />)
