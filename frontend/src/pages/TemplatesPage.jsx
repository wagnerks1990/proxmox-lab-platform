import { useEffect, useState } from 'react'
import api from '../services/api'

export default function TemplatesPage({ setMessage }) {
  const [rows,setRows]=useState([])
  const [f,setF]=useState({name:'',proxmox_node:'',source_vmid:'',enabled:true})
  const load=()=>api.get('/admin/templates').then(r=>setRows(r.data)).catch(()=>setRows([]))
  useEffect(()=>{load()},[])
  const create=async()=>{try{await api.post('/admin/templates',{...f,source_vmid:Number(f.source_vmid)});setMessage({type:'success',text:'Template created'});load()}catch(e){setMessage({type:'error',text:JSON.stringify(e?.response?.data?.detail||'Failed')})}}
  return <section className='panel'><h2>Templates</h2><div className='group'><input className='input' placeholder='Name' value={f.name} onChange={e=>setF({...f,name:e.target.value})}/><input className='input' placeholder='Node' value={f.proxmox_node} onChange={e=>setF({...f,proxmox_node:e.target.value})}/><input className='input' placeholder='Source VMID' value={f.source_vmid} onChange={e=>setF({...f,source_vmid:e.target.value})}/><button className='btn' onClick={create}>Create Template</button></div><table className='table2'><thead><tr><th>Name</th><th>Node</th><th>VMID</th><th>Enabled</th></tr></thead><tbody>{rows.map(t=><tr key={t.id}><td>{t.name}</td><td>{t.proxmox_node}</td><td>{t.source_vmid}</td><td>{String(t.enabled)}</td></tr>)}</tbody></table></section>
}
