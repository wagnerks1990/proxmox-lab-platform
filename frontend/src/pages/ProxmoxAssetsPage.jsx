import { useEffect, useMemo, useState } from 'react'
import api from '../services/api'

export default function ProxmoxAssetsPage() {
  const [inventory, setInventory] = useState(null)
  const [readiness, setReadiness] = useState(null)
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const [jobs, setJobs] = useState([])
  const [jobDetails, setJobDetails] = useState({})
  const [hostAccess, setHostAccess] = useState(null)
  const [assetServer, setAssetServer] = useState({ iso: null, ct_template: null })

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
      await loadJobs()
      try {
        const clusters = await api.get('/admin/proxmox/clusters')
        const active = (clusters.data || []).find(c => c.is_active)
        if (active?.id) {
          const hs = await api.get(`/admin/proxmox/host-access/status?cluster_id=${active.id}`)
          setHostAccess(hs.data)
          const [isoSrv, ctSrv] = await Promise.all([
            api.get(`/admin/proxmox/asset-server/status?kind=iso&cluster_id=${active.id}`),
            api.get(`/admin/proxmox/asset-server/status?kind=ct_template&cluster_id=${active.id}`),
          ])
          setAssetServer({ iso: isoSrv.data, ct_template: ctSrv.data })
        }
      } catch (_) {}
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

  const effectiveIsoSourceUrl = (isoForm.source_url || '').trim() || (hostAccess?.asset_source_iso_base_url && isoForm.filename ? `${hostAccess.asset_source_iso_base_url}/${isoForm.filename}` : '')
  const effectiveCtSourceUrl = (ctForm.source_url || '').trim() || (hostAccess?.asset_source_ct_base_url && ctForm.filename ? `${hostAccess.asset_source_ct_base_url}/${ctForm.filename}` : '')

  const isoDefaultTargets = useMemo(() => {
    const missing = readiness?.missing_isos_by_node || {}
    if (!isoForm.filename) return []
    return onlineNodes.filter((n) => (missing[n] || []).includes(isoForm.filename))
  }, [onlineNodes, readiness, isoForm.filename])

  const ctDefaultTargets = useMemo(() => {
    const missing = readiness?.missing_ct_templates_by_node || {}
    if (!ctForm.filename) return []
    return onlineNodes.filter((n) => (missing[n] || []).some((v) => String(v).split('/').pop() === ctForm.filename))
  }, [onlineNodes, readiness, ctForm.filename])

  const loadJobs = async () => {
    const { data } = await api.get('/admin/proxmox/assets/sync-jobs?limit=20')
    setJobs(data?.items || [])
    return data?.items || []
  }

  const runIsoSync = async () => {
    setBusy(true); setMsg('')
    try {
      const { data } = await api.post('/admin/proxmox/assets/sync/iso', { ...isoForm, source_url: effectiveIsoSourceUrl, storage_id: 'local' })
      await loadJobs()
      await load()
    } catch (e) { setMsg(JSON.stringify(e?.response?.data?.detail || e.message)) } finally { setBusy(false) }
  }

  const runCtSync = async () => {
    setBusy(true); setMsg('')
    try {
      const { data } = await api.post('/admin/proxmox/assets/sync/ct-template', { ...ctForm, source_url: effectiveCtSourceUrl, storage_id: 'local' })
      await loadJobs()
      await load()
    } catch (e) { setMsg(JSON.stringify(e?.response?.data?.detail || e.message)) } finally { setBusy(false) }
  }

  const runVmSync = async () => {
    setBusy(true); setMsg('')
    try {
      const payload = { ...vmForm, source_vmid: Number(vmForm.source_vmid) }
      const { data } = await api.post('/admin/proxmox/assets/sync/vm-template', payload)
      await loadJobs()
    } catch (e) { setMsg(JSON.stringify(e?.response?.data?.detail || e.message)) } finally { setBusy(false) }
  }

  const fetchJob = async (jobId) => {
    const { data } = await api.get(`/admin/proxmox/assets/sync-jobs/${jobId}`)
    setJobDetails(prev => ({ ...prev, [jobId]: data }))
  }

  const status = String(readiness?.status || '').toUpperCase()
  const tone = status === 'PASS' ? '#065f46' : status === 'WARN' ? '#92400e' : '#991b1b'
  const bg = status === 'PASS' ? '#ecfdf5' : status === 'WARN' ? '#fffbeb' : '#fef2f2'

  const vmSyncSupported = hostAccess?.mode === 'host_runner'
  const assetServerManageSupported = hostAccess?.mode === 'host_runner'


  useEffect(() => {
    if (!jobs.length) return
    const active = jobs.some(j => ['queued', 'syncing'].includes(String(j.state || '').toLowerCase()))
    if (!active) return
    const t = setInterval(async () => {
      try {
        const latest = await loadJobs()
        const hadActive = latest.some(j => ['queued', 'syncing'].includes(String(j.state || '').toLowerCase()))
        if (!hadActive) {
          await load()
        }
      } catch (_) {}
    }, 3000)
    return () => clearInterval(t)
  }, [jobs])

  const assetServerAction = async (kind, action) => {
    setBusy(true); setMsg('')
    try {
      const clusters = await api.get('/admin/proxmox/clusters')
      const active = (clusters.data || []).find(c => c.is_active)
      if (!active?.id) return
      await api.post(`/admin/proxmox/asset-server/${action}`, { kind, cluster_id: active.id })
      await load()
    } catch (e) { setMsg(JSON.stringify(e?.response?.data?.detail || e.message)) } finally { setBusy(false) }
  }

  return <section className='panel'>
    <h3>Proxmox Assets</h3>
    {msg ? <p className='muted'>{msg}</p> : null}
    <div className='group'>
      <button disabled={busy} onClick={load}>Refresh inventory/readiness</button>
      {readiness?.generated_at ? <span className='muted'>Generated: {readiness.generated_at}</span> : null}
    </div>

    <div className='panel'>
      <h4>Asset Source Server</h4>
      <p className='muted'>ISO base URL: {hostAccess?.asset_source_iso_base_url || 'not configured'}</p>
      <p className='muted'>CT base URL: {hostAccess?.asset_source_ct_base_url || 'not configured'}</p>
      {!assetServerManageSupported ? <p className='muted'>Host runner is not configured. Configure Host Access in Proxmox Setup before the app can manage source file serving.</p> : null}
      <p className='muted'>Asset server management is not configured, but sync can still run if the source URL is reachable.</p>
      <table className='vm-table'><thead><tr><th>Kind</th><th>Status</th><th>Source Node</th><th>Actions</th></tr></thead><tbody>
        {['iso','ct_template'].map(k => {
          const s = assetServer[k]
          return <tr key={k}><td>{k}</td><td style={{color:s?.status==='running'?'#065f46':(s?.status==='stopped'?'#92400e':'#b45309')}}>{s?.status || 'unknown'}</td><td>{s?.source_node || '-'}</td><td><div className='group'><button disabled={busy || !assetServerManageSupported} onClick={()=>assetServerAction(k,'install')}>Install/Update</button><button disabled={busy || !assetServerManageSupported} onClick={()=>assetServerAction(k,'start')}>Start</button><button disabled={busy || !assetServerManageSupported} onClick={()=>assetServerAction(k,'stop')}>Stop</button></div></td></tr>
        })}
      </tbody></table>
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
      {!hostAccess?.asset_source_iso_base_url ? <p className='muted'>Configure static asset source URLs or host runner in Proxmox Setup.</p> : null}
      <div className='group'>
        <select className='input' value={isoForm.filename} onChange={e=>setIsoForm({...isoForm, filename:e.target.value})}><option value=''>Select missing ISO</option>{missingIsoNames.map(v=><option key={v} value={v}>{v}</option>)}</select>
        <input className='input' placeholder='Source URL (http/https)' value={effectiveIsoSourceUrl} onChange={e=>setIsoForm({...isoForm, source_url:e.target.value})}/>
        <select className='input' multiple value={isoForm.target_nodes} onChange={e=>setIsoForm({...isoForm, target_nodes:[...e.target.selectedOptions].map(o=>o.value)})}>{onlineNodes.map(n=><option key={n} value={n}>{n}{isoForm.target_nodes.includes(n) ? ' ✓' : ''}</option>)}</select>
        <button type='button' disabled={busy || isoDefaultTargets.length===0} onClick={()=>setIsoForm({...isoForm, target_nodes: isoDefaultTargets})}>Use missing/constrained nodes</button>
        <button disabled={busy || !effectiveIsoSourceUrl || !isoForm.filename || isoForm.target_nodes.length===0} onClick={runIsoSync}>Sync ISO</button>
      </div>
    </div>

    <div className='panel'>
      <h4>CT Template Sync</h4>
      {!hostAccess?.asset_source_ct_base_url ? <p className='muted'>Configure static asset source URLs or host runner in Proxmox Setup.</p> : null}
      <div className='group'>
        <select className='input' value={ctForm.filename} onChange={e=>setCtForm({...ctForm, filename:e.target.value})}><option value=''>Select missing CT template</option>{missingCtNames.map(v=><option key={v} value={v}>{v}</option>)}</select>
        <input className='input' placeholder='Source URL (http/https)' value={effectiveCtSourceUrl} onChange={e=>setCtForm({...ctForm, source_url:e.target.value})}/>
        <select className='input' multiple value={ctForm.target_nodes} onChange={e=>setCtForm({...ctForm, target_nodes:[...e.target.selectedOptions].map(o=>o.value)})}>{onlineNodes.map(n=><option key={n} value={n}>{n}{ctForm.target_nodes.includes(n) ? ' ✓' : ''}</option>)}</select>
        <button type='button' disabled={busy || ctDefaultTargets.length===0} onClick={()=>setCtForm({...ctForm, target_nodes: ctDefaultTargets})}>Use missing/constrained nodes</button>
        <button disabled={busy || !effectiveCtSourceUrl || !ctForm.filename || ctForm.target_nodes.length===0} onClick={runCtSync}>Sync CT Template</button>
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
        <button disabled={busy || !vmSyncSupported || !vmForm.source_node || !vmForm.source_vmid || !vmForm.template_name || vmForm.target_nodes.length===0} onClick={runVmSync}>Try VM Template Sync</button>
      </div>
      <p className='muted'>Mode: {hostAccess?.mode || 'api_only'}. If host runner is not configured, VM template sync stays guarded and unsupported.</p>
    </div>

    <div className='panel'>
      <h4>Sync Jobs</h4>
      <button disabled={busy} onClick={loadJobs}>Refresh Jobs</button>
      <table className='vm-table'><thead><tr><th>job_id</th><th>state</th><th>method</th><th>target_node</th><th>proxmox_upid</th><th>error</th><th>details</th></tr></thead><tbody>
        {jobs.map(j => <tr key={j.id}><td>{j.id}</td><td>{j.state}</td><td>{j.method}</td><td>{j.target_node}</td><td>{j.proxmox_upid || '-'}</td><td>{j.error || '-'}</td><td><button onClick={()=>fetchJob(j.id)}>Load logs</button></td></tr>)}
      </tbody></table>
      {Object.entries(jobDetails).map(([id, d]) => <pre key={id} className='muted' style={{whiteSpace:'pre-wrap'}}>Job {id}: {JSON.stringify(d, null, 2)}</pre>)}
    </div>
  </section>
}
