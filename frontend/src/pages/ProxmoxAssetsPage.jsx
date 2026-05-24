import { useEffect, useMemo, useState } from 'react'
import api from '../services/api'

export default function ProxmoxAssetsPage() {
  const [inventory, setInventory] = useState(null)
  const [readiness, setReadiness] = useState(null)
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const [jobs, setJobs] = useState([])
  const [jobDetails, setJobDetails] = useState({})

  const [isoForm, setIsoForm] = useState({ filename: '', source_url: '', target_nodes: [] })
  const [ctForm, setCtForm] = useState({ filename: '', source_url: '', target_nodes: [] })
  const [vmForm, setVmForm] = useState({ source_node: '', source_vmid: '', template_name: '', storage_id: 'local-lvm', target_nodes: [] })

  const load = async () => {
    setBusy(true); setMsg('')
    try {
      const [inv, ready] = await Promise.all([
        api.get('/admin/proxmox/assets/inventory'),
        api.get('/admin/proxmox/assets/readiness'),
      ])
      setInventory(inv.data)
      setReadiness(ready.data)
    } catch (e) {
      setMsg(JSON.stringify(e?.response?.data?.detail || e.message))
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => { load() }, [])

  const onlineNodes = useMemo(() => (inventory?.nodes || []).filter(n => ['online','up'].includes(String(n.status||'').toLowerCase())).map(n => n.node), [inventory])

  const missingIsoNames = useMemo(() => {
    const s = new Set()
    Object.values(readiness?.missing_isos_by_node || {}).forEach(arr => (arr || []).forEach(v => s.add(v)))
    return [...s]
  }, [readiness])

  const missingCtNames = useMemo(() => {
    const s = new Set()
    Object.values(readiness?.missing_ct_templates_by_node || {}).forEach(arr => (arr || []).forEach(v => s.add(String(v).split('/').pop())))
    return [...s]
  }, [readiness])

  const pushJobs = (newJobs=[]) => setJobs(prev => [...newJobs, ...prev])

  const runIsoSync = async () => {
    setBusy(true); setMsg('')
    try {
      const { data } = await api.post('/admin/proxmox/assets/sync/iso', { ...isoForm, storage_id: 'local' })
      pushJobs(data?.jobs || [])
      await load()
    } catch (e) { setMsg(JSON.stringify(e?.response?.data?.detail || e.message)) } finally { setBusy(false) }
  }

  const runCtSync = async () => {
    setBusy(true); setMsg('')
    try {
      const { data } = await api.post('/admin/proxmox/assets/sync/ct-template', { ...ctForm, storage_id: 'local' })
      pushJobs(data?.jobs || [])
      await load()
    } catch (e) { setMsg(JSON.stringify(e?.response?.data?.detail || e.message)) } finally { setBusy(false) }
  }

  const runVmSync = async () => {
    setBusy(true); setMsg('')
    try {
      const payload = { ...vmForm, source_vmid: Number(vmForm.source_vmid) }
      const { data } = await api.post('/admin/proxmox/assets/sync/vm-template', payload)
      pushJobs(data?.jobs || [])
    } catch (e) { setMsg(JSON.stringify(e?.response?.data?.detail || e.message)) } finally { setBusy(false) }
  }

  const fetchJob = async (jobId) => {
    const { data } = await api.get(`/admin/proxmox/assets/sync-jobs/${jobId}`)
    setJobDetails(prev => ({ ...prev, [jobId]: data }))
  }

  const status = String(readiness?.status || '').toUpperCase()
  const tone = status === 'PASS' ? '#065f46' : status === 'WARN' ? '#92400e' : '#991b1b'
  const bg = status === 'PASS' ? '#ecfdf5' : status === 'WARN' ? '#fffbeb' : '#fef2f2'

  return <section className='panel'>
    <h3>Proxmox Assets</h3>
    {msg ? <p className='muted'>{msg}</p> : null}
    <div className='group'>
      <button disabled={busy} onClick={load}>Refresh inventory/readiness</button>
      {readiness?.generated_at ? <span className='muted'>Generated: {readiness.generated_at}</span> : null}
    </div>

    <div className='panel'>
      <h4>Readiness <span style={{padding:'2px 8px', borderRadius:8, background:bg, color:tone}}>{status || 'UNKNOWN'}</span></h4>
      <p><strong>Asset-ready nodes:</strong> {(readiness?.asset_ready_nodes || []).join(', ') || 'none'}</p>
      <p style={{color:'#92400e'}}><strong>Constrained nodes:</strong> {(readiness?.constrained_nodes || []).join(', ') || 'none'}</p>
      <p><strong>Recommended next steps:</strong> {(readiness?.recommended_next_steps || []).join(' | ') || 'none'}</p>
      <pre className='muted' style={{whiteSpace:'pre-wrap'}}>vm_template_vmid_by_node: {JSON.stringify(readiness?.vm_template_vmid_by_node || {}, null, 2)}</pre>
    </div>

    <div className='panel'>
      <h4>Inventory</h4>
      <p><strong>Nodes:</strong> {(inventory?.nodes || []).map(n => `${n.node} (${n.status})`).join(', ') || 'none'}</p>
      <p><strong>CT templates:</strong> {(inventory?.ct_templates_by_node || []).length === 0 ? 'empty on all nodes' : 'present'}</p>
      <table className='vm-table'><thead><tr><th>Node</th><th>ISOs</th><th>CT Templates</th><th>VM Templates</th></tr></thead><tbody>
        {(inventory?.nodes || []).map(n => {
          const iso = (inventory?.iso_by_node || []).find(x => x.node === n.node)?.items || []
          const ct = (inventory?.ct_templates_by_node || []).find(x => x.node === n.node)?.items || []
          const vm = (inventory?.vm_templates_by_node || []).find(x => x.node === n.node)?.templates || []
          return <tr key={n.node}><td>{n.node}</td><td>{iso.map(i=>i.filename).join(', ') || '-'}</td><td>{ct.map(i=>i.filename).join(', ') || '-'}</td><td>{vm.map(t=>`${t.name}(${t.vmid})`).join(', ') || '-'}</td></tr>
        })}
      </tbody></table>
    </div>

    <div className='panel'>
      <h4>ISO Sync</h4>
      <div className='group'>
        <select className='input' value={isoForm.filename} onChange={e=>setIsoForm({...isoForm, filename:e.target.value})}><option value=''>Select missing ISO</option>{missingIsoNames.map(v=><option key={v} value={v}>{v}</option>)}</select>
        <input className='input' placeholder='Source URL (http/https)' value={isoForm.source_url} onChange={e=>setIsoForm({...isoForm, source_url:e.target.value})}/>
        <select className='input' multiple value={isoForm.target_nodes} onChange={e=>setIsoForm({...isoForm, target_nodes:[...e.target.selectedOptions].map(o=>o.value)})}>{onlineNodes.map(n=><option key={n} value={n}>{n}</option>)}</select>
        <button disabled={busy || !isoForm.source_url || !isoForm.filename || isoForm.target_nodes.length===0} onClick={runIsoSync}>Sync ISO</button>
      </div>
    </div>

    <div className='panel'>
      <h4>CT Template Sync</h4>
      <div className='group'>
        <select className='input' value={ctForm.filename} onChange={e=>setCtForm({...ctForm, filename:e.target.value})}><option value=''>Select missing CT template</option>{missingCtNames.map(v=><option key={v} value={v}>{v}</option>)}</select>
        <input className='input' placeholder='Source URL (http/https)' value={ctForm.source_url} onChange={e=>setCtForm({...ctForm, source_url:e.target.value})}/>
        <select className='input' multiple value={ctForm.target_nodes} onChange={e=>setCtForm({...ctForm, target_nodes:[...e.target.selectedOptions].map(o=>o.value)})}>{onlineNodes.map(n=><option key={n} value={n}>{n}</option>)}</select>
        <button disabled={busy || !ctForm.source_url || !ctForm.filename || ctForm.target_nodes.length===0} onClick={runCtSync}>Sync CT Template</button>
      </div>
      {missingCtNames.length===0 ? <p className='muted'>No missing CT templates detected (empty inventory handled).</p> : null}
    </div>

    <div className='panel'>
      <h4>VM Template Sync (Guarded)</h4>
      <div className='group'>
        <input className='input' placeholder='Source node' value={vmForm.source_node} onChange={e=>setVmForm({...vmForm, source_node:e.target.value})}/>
        <input className='input' placeholder='Source VMID' value={vmForm.source_vmid} onChange={e=>setVmForm({...vmForm, source_vmid:e.target.value})}/>
        <input className='input' placeholder='Template name' value={vmForm.template_name} onChange={e=>setVmForm({...vmForm, template_name:e.target.value})}/>
        <select className='input' multiple value={vmForm.target_nodes} onChange={e=>setVmForm({...vmForm, target_nodes:[...e.target.selectedOptions].map(o=>o.value)})}>{onlineNodes.map(n=><option key={n} value={n}>{n}</option>)}</select>
        <button disabled={busy || !vmForm.source_node || !vmForm.source_vmid || !vmForm.template_name || vmForm.target_nodes.length===0} onClick={runVmSync}>Try VM Template Sync</button>
      </div>
      <p className='muted'>If command runner is not configured, backend returns unsupported/not configured. No fake success is shown.</p>
    </div>

    <div className='panel'>
      <h4>Sync Jobs</h4>
      <table className='vm-table'><thead><tr><th>job_id</th><th>state</th><th>method</th><th>target_node</th><th>proxmox_upid</th><th>error</th><th>details</th></tr></thead><tbody>
        {jobs.map(j => <tr key={j.job_id}><td>{j.job_id}</td><td>{j.state}</td><td>{j.method}</td><td>{j.target_node}</td><td>{j.proxmox_upid || '-'}</td><td>{j.error || '-'}</td><td><button onClick={()=>fetchJob(j.job_id)}>Load logs</button></td></tr>)}
      </tbody></table>
      {Object.entries(jobDetails).map(([id, d]) => <pre key={id} className='muted' style={{whiteSpace:'pre-wrap'}}>Job {id}: {JSON.stringify(d, null, 2)}</pre>)}
    </div>
  </section>
}
