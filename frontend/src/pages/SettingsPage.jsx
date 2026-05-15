import { useEffect, useState } from 'react'
import api from '../services/api'

export default function SettingsPage({ setMessage }) {
  const [s,setS]=useState(null)
  useEffect(()=>{api.get('/admin/settings/protocols').then(r=>setS(r.data))},[])
  const save=async()=>{try{await api.patch('/admin/settings/protocols',s);setMessage({type:'success',text:'Settings saved'})}catch{setMessage({type:'error',text:'Save failed'})}}
  if(!s) return <section className='panel'><h2>Settings</h2></section>
  return <section className='panel'><h2>Protocol Settings</h2><div className='group'><input className='input' value={s.terminal_gateway_url||''} onChange={e=>setS({...s,terminal_gateway_url:e.target.value})} placeholder='Terminal Gateway URL'/><input className='input' value={s.default_ssh_port} onChange={e=>setS({...s,default_ssh_port:Number(e.target.value)})} placeholder='SSH Port'/></div><div className='group'><label><input type='checkbox' checked={s.enable_web_terminal} onChange={e=>setS({...s,enable_web_terminal:e.target.checked})}/> Web Terminal</label><label><input type='checkbox' checked={s.enable_rdp} onChange={e=>setS({...s,enable_rdp:e.target.checked})}/> RDP</label><label><input type='checkbox' checked={s.enable_spice} onChange={e=>setS({...s,enable_spice:e.target.checked})}/> SPICE</label><label><input type='checkbox' checked={s.enable_novnc} onChange={e=>setS({...s,enable_novnc:e.target.checked})}/> noVNC</label></div><button className='btn' onClick={save}>Save</button></section>
}
