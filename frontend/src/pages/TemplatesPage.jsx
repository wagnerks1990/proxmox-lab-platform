import { useEffect, useState } from 'react'
import api from '../services/api'

export default function TemplatesPage({ setMessage }) {
  const [rows,setRows]=useState([])
  const [filters,setFilters]=useState({cluster:'',node:''})
  const [f,setF]=useState({name:'',proxmox_node:'',source_vmid:'',enabled:true,operating_system:'linux',default_protocols:'novnc,ssh',description:''})
  const load=()=>api.get('/admin/templates').then(r=>setRows(r.data)).catch(()=>setRows([]))
  useEffect(()=>{load()},[])
  const create=async()=>{try{await api.post('/admin/templates',{...f,source_vmid:Number(f.source_vmid)});setMessage({type:'success',text:'Template created'});load()}catch(e){setMessage({type:'error',text:JSON.stringify(e?.response?.data?.detail||'Failed')})}}
  const view = rows.filter(t => (!filters.node || (t.proxmox_node||'').includes(filters.node)))
  return <section className='panel'><h2>Templates</h2><div className='group'><input className='input' placeholder='Name' value={f.name} onChange={e=>setF({...f,name:e.target.value})}/><input className='input' placeholder='Node' value={f.proxmox_node} onChange={e=>setF({...f,proxmox_node:e.target.value})}/><input className='input' placeholder='Source VMID' value={f.source_vmid} onChange={e=>setF({...f,source_vmid:e.target.value})}/><input className='input' placeholder='OS' value={f.operating_system} onChange={e=>setF({...f,operating_system:e.target.value})}/><input className='input' placeholder='Protocol defaults' value={f.default_protocols} onChange={e=>setF({...f,default_protocols:e.target.value})}/><input className='input' placeholder='Description' value={f.description} onChange={e=>setF({...f,description:e.target.value})}/><button className='btn' onClick={create}>Create Template</button></div><div className='group'><input className='input' placeholder='Filter cluster' value={filters.cluster} onChange={e=>setFilters({...filters,cluster:e.target.value})}/><input className='input' placeholder='Filter node' value={filters.node} onChange={e=>setFilters({...filters,node:e.target.value})}/></div><table className='table2'><thead><tr><th>Name</th><th>Cluster</th><th>Node</th><th>VMID</th><th>OS</th><th>Protocols</th><th>Enabled</th></tr></thead><tbody>{view.map(t=><tr key={t.id}><td>{t.name}</td><td>{filters.cluster||'-'}</td><td>{t.proxmox_node}</td><td>{t.source_vmid}</td><td>{t.operating_system||'-'}</td><td>{t.default_protocols||'-'}</td><td>{String(t.enabled)}</td></tr>)}</tbody></table></section>
}
