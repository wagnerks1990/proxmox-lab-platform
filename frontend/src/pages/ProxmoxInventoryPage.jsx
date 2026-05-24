import { useEffect, useMemo, useState } from 'react'
import api from '../services/api'

export default function ProxmoxInventoryPage(){
  const [rows,setRows]=useState([])
  const [templates,setTemplates]=useState([])
  const [filters,setFilters]=useState({q:'',status:'',node:'',template:''})
  const [busy,setBusy]=useState(false)
  const [availability,setAvailability]=useState([])
  const [msg,setMsg]=useState('')

  const load = async ()=>{
    setBusy(true); setMsg('')
    try {
      const [inv,disc,av] = await Promise.all([api.get('/admin/proxmox/inventory/vms'), api.get('/admin/proxmox/templates/discovered'), api.get('/admin/proxmox/templates/availability')])
      setRows(Array.isArray(inv.data)?inv.data:[])
      setTemplates(Array.isArray(disc.data)?disc.data:[])
      setAvailability(Array.isArray(av.data)?av.data:[])
    } catch(e){ setMsg(JSON.stringify(e?.response?.data?.detail || e.message)) }
    finally{ setBusy(false) }
  }
  useEffect(()=>{ load() },[])

  const act = async (node, vmid, action)=>{
    setBusy(true)
    try { await api.post(`/admin/proxmox/vms/${encodeURIComponent(node)}/${vmid}/${action}`); await load(); }
    catch(e){ setMsg(JSON.stringify(e?.response?.data?.detail || e.message)) }
    finally{ setBusy(false) }
  }

  const importOne = async (t)=>{
    setBusy(true)
    try { await api.post('/admin/proxmox/templates/import', {name:t.name, proxmox_node:t.node, source_vmid:t.vmid, enabled:true}); await load(); }
    catch(e){ setMsg(JSON.stringify(e?.response?.data?.detail || e.message)) }
    finally{ setBusy(false) }
  }

  const syncAll = async ()=>{ setBusy(true); try { await api.post('/admin/proxmox/templates/sync', {}); await load(); } catch(e){ setMsg(JSON.stringify(e?.response?.data?.detail || e.message)) } finally { setBusy(false) } }
  const syncTemplatePlan = async (t)=>{ setBusy(true); try { const {data}=await api.post('/admin/proxmox/assets/sync-template',{template_vmid:t.vmid,source_node:t.node,target_nodes:[],confirm:true}); setMsg(data?.message||'Sync request sent') } catch(e){ setMsg(JSON.stringify(e?.response?.data?.detail || e.message)) } finally { setBusy(false) } }

  const filtered = useMemo(()=>rows.filter(r=>{
    if (filters.status && (r.status||'')!==filters.status) return false
    if (filters.node && (r.node||'')!==filters.node) return false
    if (filters.template==='templates' && !r.template) return false
    if (filters.template==='vms' && r.template) return false
    if (filters.q && !(String(r.name||'').toLowerCase().includes(filters.q.toLowerCase()) || String(r.vmid).includes(filters.q))) return false
    return true
  }),[rows,filters])

  const nodes = [...new Set(rows.map(r=>r.node).filter(Boolean))]
  const statuses = [...new Set(rows.map(r=>r.status).filter(Boolean))]

  return <section className='panel'>
    <h3>Proxmox Inventory</h3>
    <p className='muted'>This page controls Proxmox inventory directly. Student VM ownership rules apply only to lab-assigned VMs.</p>
    {msg ? <p className='muted'>{msg}</p> : null}
    <div className='group'>
      <input className='input' placeholder='Search name/vmid' value={filters.q} onChange={e=>setFilters({...filters,q:e.target.value})}/>
      <select className='input' value={filters.node} onChange={e=>setFilters({...filters,node:e.target.value})}><option value=''>All nodes</option>{nodes.map(n=><option key={n}>{n}</option>)}</select>
      <select className='input' value={filters.status} onChange={e=>setFilters({...filters,status:e.target.value})}><option value=''>All status</option>{statuses.map(s=><option key={s}>{s}</option>)}</select>
      <select className='input' value={filters.template} onChange={e=>setFilters({...filters,template:e.target.value})}><option value=''>VMs + templates</option><option value='templates'>Templates only</option><option value='vms'>VMs only</option></select>
      <button disabled={busy} onClick={load}>Refresh</button>
      <button disabled={busy} onClick={syncAll}>Sync all templates</button>
    </div>

    <h4>Discovered templates</h4><p className='muted'>Template availability across nodes is shown below.</p>
    <table className='vm-table'><thead><tr><th>VMID</th><th>Name</th><th>Node</th><th>Imported</th><th>Available Nodes</th><th>Action</th></tr></thead><tbody>
      {templates.map(t=>{ const av = availability.find(a => Number(a.template_vmid)===Number(t.vmid)); return <tr key={`${t.node}-${t.vmid}`}><td>{t.vmid}</td><td>{t.name}</td><td>{t.node}</td><td>{t.already_imported?'Yes':'No'}</td><td>{av ? (av.available_nodes||[]).join(', ') : '—'}{av?.warnings?.length?<div className='muted'>{av.warnings.join('; ')}</div>:null}</td><td>{t.already_imported?'—':<button disabled={busy} onClick={()=>importOne(t)}>Import</button>}<button disabled={busy} onClick={()=>syncTemplatePlan(t)}>Sync/Prepare</button></td></tr>})}
    </tbody></table>

    <h4>All Proxmox VMs/Templates</h4>
    <table className='vm-table'><thead><tr><th>Node</th><th>VMID</th><th>Name</th><th>Status</th><th>Template</th><th>Linked</th><th>Owner</th><th>Actions</th></tr></thead><tbody>
      {filtered.map(r=><tr key={`${r.node}-${r.vmid}`}><td>{r.node}</td><td>{r.vmid}</td><td>{r.name}</td><td>{r.status}</td><td>{r.template?'Yes':'No'}</td><td>{r.app_linked?'Yes':'No'}</td><td>{r.owner_username||'-'}</td><td><div className='group'>{!r.template && <><button disabled={busy} onClick={()=>act(r.node,r.vmid,'start')}>Start</button><button disabled={busy} onClick={()=>act(r.node,r.vmid,'stop')}>Stop</button><button disabled={busy} onClick={()=>act(r.node,r.vmid,'reboot')}>Reboot</button><button disabled={busy} onClick={()=>act(r.node,r.vmid,'shutdown')}>Shutdown</button></>}</div></td></tr>)}
    </tbody></table>
  </section>
}
