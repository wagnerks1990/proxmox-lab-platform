import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import { listPools, createPool, updatePool, deletePool, togglePoolEnabled, togglePoolMaintenance, readinessPool, planPool } from '../services/poolsApi'

const emptyForm = { name:'', description:'', pool_type:'persistent', template_vmid:'', template_node:'', default_protocol:'NOVNC', desired_size:0, enabled:true, maintenance_mode:false }

export default function PoolsPage(){
  const [rows,setRows]=useState([])
  const [templates,setTemplates]=useState([])
  const [form,setForm]=useState(emptyForm)
  const [editing,setEditing]=useState(null)
  const [msg,setMsg]=useState('')
  const [readiness,setReadiness]=useState({})
  const [plan,setPlan]=useState({})

  const [loading,setLoading]=useState(false)
  const load = ()=>{ setLoading(true); return listPools().then(setRows).catch(()=>setRows([])).finally(()=>setLoading(false)) }
  useEffect(()=>{ load(); api.get('/templates').then(r=>setTemplates(Array.isArray(r.data)?r.data:[])).catch(()=>setTemplates([])) },[])

  const save = async ()=> {
    try{
      const payload = { ...form, template_vmid: form.template_vmid ? Number(form.template_vmid) : null, desired_size: Number(form.desired_size||0) }
      if (editing) await updatePool(editing, payload); else await createPool(payload)
      setForm(emptyForm); setEditing(null); setMsg('Pool saved. No automatic VM provisioning was triggered.'); await load()
    }catch(e){ setMsg(JSON.stringify(e?.response?.data?.detail||'Save failed'))}
  }

  const selectedTemplate = templates.find(t=>String(t.source_vmid)===String(form.template_vmid))
  return <section>
    <h2>Pools</h2>
    <p className='muted'>Desktop pools group templates, placement policy, and desired VM counts for lab provisioning.</p>
    {msg?<p className='muted'>{msg}</p>:null}
    <div className='panel'>
      <h3>{editing?'Edit Pool':'Create Pool'}</h3>
      <div className='group'>
        <input className='input' placeholder='Name' value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/>
        <input className='input' placeholder='Description' value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/>
        <select className='input' value={form.pool_type} onChange={e=>setForm({...form,pool_type:e.target.value})}><option value='persistent'>persistent</option><option value='non_persistent'>non_persistent</option></select>
        <select className='input' value={form.default_protocol} onChange={e=>setForm({...form,default_protocol:e.target.value})}><option>NOVNC</option><option>SSH_WS</option><option>RDP</option></select>
        <input className='input' type='number' min='0' value={form.desired_size} onChange={e=>setForm({...form,desired_size:e.target.value})}/>
        <select className='input' value={form.template_vmid} onChange={e=>{const v=e.target.value; const t=templates.find(x=>String(x.source_vmid)===v); setForm({...form,template_vmid:v,template_node:t?.proxmox_node||''})}}>
          <option value=''>Select imported template</option>
          {templates.map(t=><option key={t.id} value={t.source_vmid}>{t.name} (VMID {t.source_vmid}, {t.proxmox_node})</option>)}
        </select>
        <label><input type='checkbox' checked={form.enabled} onChange={e=>setForm({...form,enabled:e.target.checked})}/> enabled</label>
        <label><input type='checkbox' checked={form.maintenance_mode} onChange={e=>setForm({...form,maintenance_mode:e.target.checked})}/> maintenance</label>
        <button onClick={save} disabled={!form.name}>Save</button>
      </div>
      {selectedTemplate ? <p className='muted'>Selected template: {selectedTemplate.name} (VMID {selectedTemplate.source_vmid}, node {selectedTemplate.proxmox_node})</p> : null}
      {templates.length===0?<p className='muted'>Import Proxmox templates first, then create a desktop pool. <Link to='/admin/proxmox-inventory'>Go to Proxmox Inventory</Link></p>:null}
    </div>
    {loading?<p className='muted'>Loading pools…</p>:null}
    {!loading && rows.length===0?<p className='muted'>No desktop pools configured yet. Import templates first, then create a desktop pool.</p>:null}
    <table className='vm-table'><thead><tr><th>Name</th><th>Type</th><th>Enabled</th><th>Maintenance</th><th>Desired</th><th>Protocol</th><th>Template</th><th>Counts</th><th>Readiness</th><th>Actions</th></tr></thead><tbody>
      {rows.map(r=><tr key={r.id}><td>{r.name}</td><td>{r.pool_type}</td><td>{String(r.enabled)}</td><td>{String(r.maintenance_mode)}</td><td>{r.desired_size}</td><td>{r.default_protocol}</td><td>{r.template_vmid?`${r.template_vmid}@${r.template_node||'-'}`:'-'}</td><td><div className='muted'>VMs: {r.linked_vm_count ?? 0} · Templates: {r.linked_template_count ?? 0} · Groups: {r.linked_group_count ?? 0}</div></td><td><span style={{color:(r.readiness_status||readiness[r.id]?.status)==='WARN'?'#92400e':(r.readiness_status||readiness[r.id]?.status)==='FAIL'?'#991b1b':'#065f46'}}>{r.readiness_status||readiness[r.id]?.status||'-'}</span>{r.placement_warning?<div className='muted'>{r.placement_warning}</div>:null}{(r.constrained_nodes||[]).length?<div className='muted'>Constrained: {r.constrained_nodes.join(', ')}</div>:null}</td><td><div className='group'><button onClick={()=>{setEditing(r.id); setForm({...emptyForm,...r,template_vmid:r.template_vmid||''})}}>Edit</button><button onClick={async()=>{await togglePoolEnabled(r.id,!r.enabled); load()}}>{r.enabled?'Disable':'Enable'}</button><button onClick={async()=>{await togglePoolMaintenance(r.id,!r.maintenance_mode); load()}}>{r.maintenance_mode?'Maintenance Off':'Maintenance On'}</button><button onClick={async()=>{const x=await readinessPool(r.id); setReadiness(p=>({...p,[r.id]:x})); setMsg((x.failures||[]).concat(x.warnings||[]).join(' | ') || `Readiness ${x.status}`)}}>Readiness</button><button onClick={async()=>{const x=await planPool(r.id); setPlan(p=>({...p,[r.id]:x})); setMsg(`Plan: desired=${x.desired_size}, preview=${(x.vmid_preview||[]).join(',')}`)}}>Plan</button><button disabled title='Provisioning/prewarm is not implemented safely yet'>Prewarm (Unsupported)</button><button className='btn-danger' onClick={async()=>{if(!confirm('Delete pool app record? No Proxmox VMs are deleted automatically.')) return; await deletePool(r.id); load()}}>Delete</button></div>{plan[r.id]?.warnings?.length?<div className='muted'>Warnings: {plan[r.id].warnings.join('; ')}</div>:null}</td></tr>)}
    </tbody></table>
  </section>
}
