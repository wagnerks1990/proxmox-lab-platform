import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'
import { listPools, createPool, updatePool, deletePool, togglePoolEnabled, togglePoolMaintenance, readinessPool, planPool } from '../services/poolsApi'

const emptyForm = { name:'', description:'', pool_type:'persistent', template_vmid:'', template_node:'', default_protocol:'NOVNC', desired_size:0, enabled:true, maintenance_mode:false }
const statusClass = status => status === 'PASS' ? 'ui-status-badge--success' : status === 'WARN' ? 'ui-status-badge--warning' : status === 'FAIL' ? 'ui-status-badge--danger' : 'ui-status-badge--neutral'

export default function PoolsPage(){
  const [rows,setRows]=useState([]); const [templates,setTemplates]=useState([]); const [form,setForm]=useState(emptyForm)
  const [editing,setEditing]=useState(null); const [message,setMessage]=useState(null); const [readiness,setReadiness]=useState({}); const [plan,setPlan]=useState({}); const [loading,setLoading]=useState(false); const [loadError,setLoadError]=useState('')
  const load = async () => { setLoading(true); setLoadError(''); try { setRows(await listPools()) } catch { setRows([]); setLoadError('Unable to load desktop pools.') } finally { setLoading(false) } }
  useEffect(()=>{ load(); api.get('/templates').then(response=>setTemplates(Array.isArray(response.data)?response.data:[])).catch(()=>setTemplates([])) },[])

  const save = async event => {
    event.preventDefault()
    try {
      const payload = { ...form, template_vmid: form.template_vmid ? Number(form.template_vmid) : null, desired_size: Number(form.desired_size||0) }
      if (editing) await updatePool(editing, payload); else await createPool(payload)
      setForm(emptyForm); setEditing(null); setMessage({type:'success', text:'Pool saved. No automatic VM provisioning was triggered.'}); await load()
    } catch(error){ setMessage({type:'error', text:JSON.stringify(error?.response?.data?.detail||'Save failed')}) }
  }
  const run = async work => { try { await work() } catch (error) { setMessage({type:'error', text:JSON.stringify(error?.response?.data?.detail || 'Request failed')}) } }
  const selectedTemplate = templates.find(template=>String(template.source_vmid)===String(form.template_vmid))

  return <section className='page-shell' aria-labelledby='pools-title'>
    <header className='ui-page-header'><div><p className='muted'>Teaching</p><h2 id='pools-title'>Pools</h2><p className='ui-page-header__description'>Group templates, placement policy, and desired capacity for classroom provisioning.</p></div><button onClick={load} disabled={loading}>{loading?'Refreshing…':'Refresh'}</button></header>
    {message ? <p className={`msg ${message.type}`} role={message.type==='error'?'alert':'status'} aria-live='polite'>{message.text}</p> : null}
    {loadError ? <p className='msg error' role='alert'>{loadError}</p> : null}

    <section className='panel' aria-labelledby='pool-form-title'>
      <h3 id='pool-form-title'>{editing?'Edit pool':'Create pool'}</h3>
      <form className='ui-form-grid' onSubmit={save}>
        <label className='ui-field'>Name<input className='input' value={form.name} onChange={event=>setForm({...form,name:event.target.value})}/></label>
        <label className='ui-field'>Description<input className='input' value={form.description} onChange={event=>setForm({...form,description:event.target.value})}/></label>
        <label className='ui-field'>Pool type<select className='input' value={form.pool_type} onChange={event=>setForm({...form,pool_type:event.target.value})}><option value='persistent'>Persistent</option><option value='non_persistent'>Non-persistent</option></select></label>
        <label className='ui-field'>Default protocol<select className='input' value={form.default_protocol} onChange={event=>setForm({...form,default_protocol:event.target.value})}><option>NOVNC</option><option value='SSH_WS' disabled>SSH (unavailable)</option><option>RDP</option></select></label>
        <label className='ui-field'>Desired VM count<input className='input' type='number' min='0' inputMode='numeric' value={form.desired_size} onChange={event=>setForm({...form,desired_size:event.target.value})}/></label>
        <label className='ui-field'>Imported template<select className='input' value={form.template_vmid} onChange={event=>{const value=event.target.value; const template=templates.find(item=>String(item.source_vmid)===value); setForm({...form,template_vmid:value,template_node:template?.proxmox_node||''})}}><option value=''>Select a template</option>{templates.map(template=><option key={template.id} value={template.source_vmid}>{template.name} (VMID {template.source_vmid}, {template.proxmox_node})</option>)}</select></label>
        <fieldset className='ui-cluster ui-form-grid__wide'><legend>Availability</legend><label><input type='checkbox' checked={form.enabled} onChange={event=>setForm({...form,enabled:event.target.checked})}/> Enabled</label><label><input type='checkbox' checked={form.maintenance_mode} onChange={event=>setForm({...form,maintenance_mode:event.target.checked})}/> Maintenance mode</label></fieldset>
        <div className='ui-cluster ui-form-grid__wide'><button type='submit' disabled={!form.name}>Save pool</button>{editing ? <button type='button' className='ui-button--secondary' onClick={()=>{setEditing(null);setForm(emptyForm)}}>Cancel</button> : null}</div>
      </form>
      {selectedTemplate ? <p className='muted'>Selected: {selectedTemplate.name} · VMID {selectedTemplate.source_vmid} · {selectedTemplate.proxmox_node}</p> : null}
      {templates.length===0 ? <p className='muted'>Import Proxmox templates first. <Link to='/admin/proxmox-inventory'>Open Proxmox Inventory</Link>.</p> : null}
    </section>

    <section className='panel' aria-labelledby='pool-list-title'>
      <div className='panel-head'><div><h3 id='pool-list-title'>Configured pools</h3><p className='muted'>{rows.length} total</p></div></div>
      {!loading && !loadError && rows.length===0 ? <p className='muted'>No desktop pools are configured yet.</p> : null}
      {rows.length ? <div className='ui-table-wrap' role='region' aria-labelledby='pool-list-title' tabIndex='0'><table className='ui-table'><thead><tr><th scope='col'>Name</th><th scope='col'>Configuration</th><th scope='col'>Capacity</th><th scope='col'>Readiness</th><th scope='col'>Actions</th></tr></thead><tbody>
        {rows.map(pool=>{ const ready=pool.readiness_status||readiness[pool.id]?.status||'-'; return <tr key={pool.id}><th scope='row'>{pool.name}<div className='muted'>{pool.pool_type}</div></th><td>{pool.enabled?'Enabled':'Disabled'} · {pool.maintenance_mode?'Maintenance':'Available'}<div className='muted'>{pool.default_protocol} · {pool.template_vmid?`${pool.template_vmid}@${pool.template_node||'-'}`:'No template'}</div></td><td>{pool.desired_size} desired<div className='muted'>{pool.linked_vm_count ?? 0} VMs · {pool.linked_template_count ?? 0} templates · {pool.linked_group_count ?? 0} groups</div></td><td><span className={`status-badge ${statusClass(ready)}`}>{ready}</span>{pool.placement_warning?<div className='muted'>{pool.placement_warning}</div>:null}{(pool.constrained_nodes||[]).length?<div className='muted'>Constrained: {pool.constrained_nodes.join(', ')}</div>:null}</td><td><div className='ui-cluster'>
          <button aria-label={`Edit pool ${pool.name}`} onClick={()=>{setEditing(pool.id);setForm({...emptyForm,...pool,template_vmid:pool.template_vmid||''});window.scrollTo({top:0,behavior:'smooth'})}}>Edit</button>
          <button aria-label={`${pool.enabled?'Disable':'Enable'} pool ${pool.name}`} onClick={()=>run(async()=>{await togglePoolEnabled(pool.id,!pool.enabled);await load()})}>{pool.enabled?'Disable':'Enable'}</button>
          <button aria-label={`${pool.maintenance_mode?'End':'Start'} maintenance for ${pool.name}`} onClick={()=>run(async()=>{await togglePoolMaintenance(pool.id,!pool.maintenance_mode);await load()})}>{pool.maintenance_mode?'End maintenance':'Maintenance'}</button>
          <button aria-label={`Check readiness for ${pool.name}`} onClick={()=>run(async()=>{const result=await readinessPool(pool.id);setReadiness(previous=>({...previous,[pool.id]:result}));setMessage({type:result.status==='FAIL'?'error':'success',text:(result.failures||[]).concat(result.warnings||[]).join(' | ')||`Readiness ${result.status}`})})}>Readiness</button>
          <button aria-label={`Plan pool ${pool.name}`} onClick={()=>run(async()=>{const result=await planPool(pool.id);setPlan(previous=>({...previous,[pool.id]:result}));setMessage({type:'success',text:`Plan: desired=${result.desired_size}, preview=${(result.vmid_preview||[]).join(',')}`})})}>Plan</button>
          <button className='btn-danger' aria-label={`Delete pool ${pool.name}`} onClick={()=>run(async()=>{if(!confirm(`Delete pool ${pool.name}? No Proxmox VMs are deleted automatically.`))return;await deletePool(pool.id);await load()})}>Delete</button>
        </div><p className='ui-field__hint'>Prewarm is unavailable until provisioning is implemented safely.</p>{plan[pool.id]?.warnings?.length?<div className='muted'>Warnings: {plan[pool.id].warnings.join('; ')}</div>:null}</td></tr>})}
      </tbody></table></div> : null}
    </section>
  </section>
}
