import { useEffect, useState } from 'react'
import api from '../services/api'

export default function PoolsPage({ setMessage }) {
  const [rows, setRows] = useState([])
  const [form, setForm] = useState({ name:'', description:'', enabled:true, default_template_id:'', max_vms:20, max_running_vms:10, auto_start:true, recycle_on_logout:false })
  const load=()=>api.get('/admin/pools').then(r=>setRows(r.data)).catch(()=>setRows([]))
  useEffect(()=>{load()},[])
  const submit=async()=>{try{await api.post('/admin/pools',{...form,default_template_id: form.default_template_id?Number(form.default_template_id):null});setMessage({type:'success',text:'Pool created'});load()}catch(e){setMessage({type:'error',text:JSON.stringify(e?.response?.data?.detail||'Failed')})}}
  return <section className='panel'><h2>Pools</h2><div className='group'><input className='input' placeholder='Name' value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/><input className='input' placeholder='Description' value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/><input className='input' placeholder='Default Template ID' value={form.default_template_id} onChange={e=>setForm({...form,default_template_id:e.target.value})}/><button className='btn' onClick={submit}>Create Pool</button></div><table className='table2'><thead><tr><th>Name</th><th>Enabled</th><th>Default Template</th><th>Max VMs</th><th>Max Running</th><th>Auto Start</th><th>Recycle</th></tr></thead><tbody>{rows.map(r=><tr key={r.id}><td>{r.name}</td><td>{String(r.enabled)}</td><td>{r.default_template_id||'-'}</td><td>{r.max_vms}</td><td>{r.max_running_vms}</td><td>{String(r.auto_start)}</td><td>{String(r.recycle_on_logout)}</td></tr>)}</tbody></table></section>
}
