import { useEffect, useMemo, useState } from 'react'
import api from '../services/api'

const bootstrapInit = { name:'Primary Proxmox', api_url:'', verify_ssl:false, root_username:'root@pam', root_password:'', token_id:'proxmox-lab-platform' }
const manualInit = { name:'Primary Proxmox', api_url:'', verify_ssl:false, token_user:'root@pam', token_id:'proxmox-lab-platform', token_secret:'' }
const defaultsInit = { default_node:'', default_storage:'', default_bridge:'', default_template_vmid:'', clone_mode:'full', placement_policy:'', notes:'' }

export default function ProxmoxSetupPage(){
  const [clusters,setClusters]=useState([])
  const [selectedId,setSelectedId]=useState(null)
  const [loading,setLoading]=useState(false)
  const [showBootstrap,setShowBootstrap]=useState(false)
  const [msg,setMsg]=useState('')
  const [bootstrap,setBootstrap]=useState(bootstrapInit)
  const [manual,setManual]=useState(manualInit)
  const [defaultsForm,setDefaultsForm]=useState(defaultsInit)
  const [nodes,setNodes]=useState([])
  const [storage,setStorage]=useState([])
  const [templates,setTemplates]=useState([])
  const [networks,setNetworks]=useState([])
  const [readiness,setReadiness]=useState(null)
  const [assetPlanMsg, setAssetPlanMsg] = useState('')
  const [selectedTemplateVmid, setSelectedTemplateVmid] = useState('')
  const [selectedIsoId, setSelectedIsoId] = useState('')
  const [hostAccess, setHostAccess] = useState(null)
  const [hostAccessForm, setHostAccessForm] = useState({ root_username: 'root@pam', root_password: '', node_names: [] })
  const [hostAccessResult, setHostAccessResult] = useState(null)

  const activeCluster = useMemo(()=>clusters.find(c=>c.is_active),[clusters])
  const readinessStatus = String(readiness?.status || '').toUpperCase()
  const readinessTone = readinessStatus === 'PASS' ? '#065f46' : readinessStatus === 'WARN' ? '#92400e' : '#991b1b'
  const readinessBg = readinessStatus === 'PASS' ? '#ecfdf5' : readinessStatus === 'WARN' ? '#fffbeb' : '#fef2f2'

  const run = async (fn)=>{ setLoading(true); setMsg(''); try{ await fn() } catch(e){ const m = JSON.stringify(e?.response?.data?.detail || e?.response?.data || e.message); setMsg(m); setHostAccessResult({ ok:false, message:m }) } finally { setLoading(false) } }
  const loadClusters = async ()=>{ const {data} = await api.get('/admin/proxmox/clusters'); setClusters(Array.isArray(data)?data:[]) }

  useEffect(()=>{ loadClusters().catch(()=>setClusters([])) },[])
  useEffect(()=>{
    const loadHostAccess = async ()=>{
      try {
        const { data } = await api.get('/admin/proxmox/host-access/status')
        setHostAccess(data || null)
      } catch (_) {}
    }
    if (activeCluster) loadHostAccess()
  }, [activeCluster?.id])

  const refreshDiscovery = (id)=>run(async ()=>{
    const [n,s,t,net,cfg,ready] = await Promise.all([
      api.get(`/admin/proxmox/clusters/${id}/nodes`),
      api.get(`/admin/proxmox/clusters/${id}/storage`),
      api.get(`/admin/proxmox/clusters/${id}/templates`),
      api.get(`/admin/proxmox/clusters/${id}/networks`),
      api.get(`/admin/proxmox/clusters/${id}`),
      api.get(`/admin/proxmox/clusters/${id}/readiness`),
    ])
    setSelectedId(id)
    setNodes(Array.isArray(n.data)?n.data:[])
    setStorage(Array.isArray(s.data)?s.data:[])
    setTemplates(Array.isArray(t.data)?t.data:[])
    setNetworks(Array.isArray(net.data)?net.data:[])
    setReadiness(ready.data || null)
    const tpl = Array.isArray(t.data) ? t.data : []
    if (!selectedTemplateVmid && tpl.length) setSelectedTemplateVmid(String(tpl[0].vmid))
    const isos = ready.data?.isos || []
    if (!selectedIsoId && isos.length) setSelectedIsoId(isos[0].content_id || isos[0].name || '')
    setDefaultsForm({ ...defaultsInit, ...(cfg.data?.defaults || {}) })
    setMsg('Discovery refreshed.')
    const hs = await api.get(`/admin/proxmox/host-access/status?cluster_id=${id}`)
    setHostAccess(hs.data)
  })
  const bootstrapHostAccess = ()=>run(async ()=>{
    if (!selectedId) return
    const payload = { cluster_id: selectedId, ...hostAccessForm }
    await api.post('/admin/proxmox/host-access/bootstrap', payload)
    setHostAccessForm({ ...hostAccessForm, root_password: '' })
    const hs = await api.get(`/admin/proxmox/host-access/status?cluster_id=${selectedId}`)
    setHostAccess(hs.data)
    setMsg('Host access bootstrap completed.')
  })
  const validateHostAccess = ()=>run(async ()=>{
    const targetClusterId = selectedId || activeCluster?.id
    if (!targetClusterId) return
    const res = await api.post('/admin/proxmox/host-access/validate', { cluster_id: targetClusterId })
    const hs = await api.get(`/admin/proxmox/host-access/status?cluster_id=${targetClusterId}`)
    setHostAccess(hs.data)
    const resultMessage = res?.data?.message || (res?.data?.ok ? 'Host access validate completed.' : 'Host access validation did not pass.')
    setMsg(resultMessage)
    setHostAccessResult({ ok: !!res?.data?.ok, message: resultMessage, data: res?.data })
  })

  const doBootstrap = ()=>run(async ()=>{
    const {data} = await api.post('/admin/proxmox/bootstrap-root', bootstrap)
    setBootstrap({...bootstrap, root_password:''})
    if (data?.token_exists) {
      setMsg(`${data.message} Suggested actions: ${data.suggested_actions?.join(' | ')}`)
      return
    }
    await loadClusters()
    if (data?.cluster_id) await refreshDiscovery(data.cluster_id)
    setMsg('Bootstrap successful.')
  })

  const doManualToken = ()=>run(async ()=>{
    const {data} = await api.post('/admin/proxmox/clusters/manual-token', manual)
    setManual({...manual, token_secret:''})
    await loadClusters()
    if (data?.cluster_id) await refreshDiscovery(data.cluster_id)
    setMsg('Manual token saved and validated.')
  })

  const doValidate = (id)=>run(async ()=>{ await api.post(`/admin/proxmox/clusters/${id}/validate`); await loadClusters(); setMsg('Validation complete.') })
  const doActivate = (id)=>run(async ()=>{ await api.post(`/admin/proxmox/clusters/${id}/activate`); await loadClusters(); setMsg('Cluster activated.') })
  const doDelete = (id)=>run(async ()=>{ if(!window.confirm('Delete this app cluster record only?')) return; await api.delete(`/admin/proxmox/clusters/${id}`); await loadClusters(); if(selectedId===id){setSelectedId(null)} setMsg('Cluster record deleted (Proxmox VMs untouched).') })
  const doSaveDefaults = ()=>run(async ()=>{ if(!selectedId) return; await api.patch(`/admin/proxmox/clusters/${selectedId}/defaults`, { ...defaultsForm, default_template_vmid: defaultsForm.default_template_vmid ? Number(defaultsForm.default_template_vmid) : null }); setMsg('Defaults saved.') })
  const runTemplateSyncPlan = ()=>run(async ()=>{
    const selected = templates.find(t => String(t.vmid) === String(selectedTemplateVmid))
    if (!selected) { setMsg('Select a template before generating sync plan.'); return }
    const sourceNode = selected.node
    const targetNodes = nodes.map(n=>n.node_name).filter(n=>n!==sourceNode)
    const targetStorage = 'local-lvm'
    const payload = { type:'template', template_vmid: Number(selected.vmid), source_node: sourceNode, target_nodes: targetNodes, target_storage: targetStorage, mode: 'full' }
    const { data } = await api.post('/admin/proxmox/assets/sync-plan', payload)
    setAssetPlanMsg(JSON.stringify(data))
  })
  const runIsoSyncPlan = ()=>run(async ()=>{
    const isos = readiness?.isos || []
    const selected = isos.find(i => (i.content_id || i.name) === selectedIsoId)
    if (!selected) { setMsg('Select ISO/media before generating sync plan.'); return }
    const sourceNode = selected.node
    const payload = { type:'iso', source_node: sourceNode, source_storage: selected.storage, volume: selected.content_id, target_nodes: nodes.map(n=>n.node_name).filter(n=>n!==sourceNode), target_storage: 'local' }
    const { data } = await api.post('/admin/proxmox/assets/sync-plan', payload)
    setAssetPlanMsg(JSON.stringify(data))
  })

  return <section className='panel'>
    <h2>Proxmox Setup</h2>
    {activeCluster ? <div className='panel'><strong>Active cluster configured:</strong> {activeCluster.name} ({activeCluster.api_url})</div> : null}
    <p className='muted'>Root credentials are used only during bootstrap and are not stored. Token secrets are never returned by API.</p>

    <button disabled={loading} onClick={()=>setShowBootstrap(!showBootstrap)}>{showBootstrap ? 'Hide Bootstrap Forms' : 'Add another cluster / re-bootstrap'}</button>

    {(showBootstrap || !activeCluster) ? <>
      <h3>Bootstrap with Root</h3>
      <div className='group'>
        <input className='input' placeholder='Cluster name' value={bootstrap.name} onChange={e=>setBootstrap({...bootstrap,name:e.target.value})}/>
        <input className='input' placeholder='API URL' value={bootstrap.api_url} onChange={e=>setBootstrap({...bootstrap,api_url:e.target.value})}/>
        <input className='input' placeholder='Root username' value={bootstrap.root_username} onChange={e=>setBootstrap({...bootstrap,root_username:e.target.value})}/>
        <input className='input' placeholder='Token ID' value={bootstrap.token_id} onChange={e=>setBootstrap({...bootstrap,token_id:e.target.value})}/>
        <input className='input' type='password' placeholder='Root password' value={bootstrap.root_password} onChange={e=>setBootstrap({...bootstrap,root_password:e.target.value})}/>
        <label><input type='checkbox' checked={bootstrap.verify_ssl} onChange={e=>setBootstrap({...bootstrap,verify_ssl:e.target.checked})}/> Verify SSL</label>
        <button disabled={loading} onClick={doBootstrap}>Bootstrap</button>
      </div>
      <h3>Host Access</h3>
      <p className='muted'>Current mode: {hostAccess?.mode || 'api_only'}. Root password is used only during this request and is not persisted.</p>
      {hostAccess?.mode === 'static_asset_server' ? <div className='panel'><p className='muted'>Static asset server mode is active. ISO/CT source URLs can be generated.</p><p className='muted'>Host-runner command execution is disabled.</p><p className='muted'>Root password is not used in this mode.</p></div> : null}
      <div className='group'>
        {hostAccess?.mode !== 'static_asset_server' ? <>
          <input className='input' placeholder='Root username' value={hostAccessForm.root_username} onChange={e=>setHostAccessForm({...hostAccessForm, root_username:e.target.value})}/>
          <input className='input' type='password' placeholder='Root password (one-time)' value={hostAccessForm.root_password} onChange={e=>setHostAccessForm({...hostAccessForm, root_password:e.target.value})}/>
          <select className='input' multiple value={hostAccessForm.node_names} onChange={e=>setHostAccessForm({...hostAccessForm, node_names:[...e.target.selectedOptions].map(o=>o.value)})}>
            {(hostAccess?.nodes || nodes).map(n => <option key={n.node_name} value={n.node_name}>{n.node_name}</option>)}
          </select>
        </> : null}
        <button disabled={true} title='Host runner bootstrap is not enabled/configured yet.' onClick={bootstrapHostAccess}>Configure Host Runner</button>
        <button disabled={loading || !(selectedId || activeCluster?.id)} onClick={validateHostAccess}>Validate Host Access</button>
      </div>
      <p className='muted'>Host runner bootstrap is not enabled/configured yet.</p>
      {hostAccessResult ? <div className='panel' style={{borderColor: hostAccessResult.ok ? '#065f46' : '#92400e'}}><strong>Host Access Validate Result:</strong> {hostAccessResult.message}</div> : null}
      {(hostAccess?.nodes || []).length ? <ul>{hostAccess.nodes.map(n => <li key={n.node_name} className='muted'>{n.node_name}: {n.host_access_status || n.status} ({n.runner_user})</li>)}</ul> : null}

      <h3>Manual Token Fallback</h3>
      <div className='group'>
        <input className='input' placeholder='Cluster name' value={manual.name} onChange={e=>setManual({...manual,name:e.target.value})}/>
        <input className='input' placeholder='API URL' value={manual.api_url} onChange={e=>setManual({...manual,api_url:e.target.value})}/>
        <input className='input' placeholder='Token user' value={manual.token_user} onChange={e=>setManual({...manual,token_user:e.target.value})}/>
        <input className='input' placeholder='Token ID' value={manual.token_id} onChange={e=>setManual({...manual,token_id:e.target.value})}/>
        <input className='input' type='password' placeholder='Token secret' value={manual.token_secret} onChange={e=>setManual({...manual,token_secret:e.target.value})}/>
        <label><input type='checkbox' checked={manual.verify_ssl} onChange={e=>setManual({...manual,verify_ssl:e.target.checked})}/> Verify SSL</label>
        <button disabled={loading} onClick={doManualToken}>Save Manual Token</button>
      </div>
    </> : null}

    <h3>Configured Clusters</h3>
    {clusters.length===0 ? <p className='muted'>No clusters configured yet.</p> : <table className='vm-table'><thead><tr><th>Name</th><th>API URL</th><th>Token</th><th>Active</th><th>Validation</th><th>Actions</th></tr></thead><tbody>
      {clusters.map(c=><tr key={c.id}><td>{c.name}</td><td>{c.api_url}</td><td>{c.token_user} / {c.token_id}</td><td>{String(c.is_active)}</td><td>{c.last_validation_status || '-'} {c.last_validated_at || ''}</td><td><div className='group'><button disabled={loading} onClick={()=>doValidate(c.id)}>Validate</button><button disabled={loading} onClick={()=>doActivate(c.id)}>Activate</button><button disabled={loading} onClick={()=>refreshDiscovery(c.id)}>Refresh Discovery</button><button disabled={loading} onClick={()=>doDelete(c.id)}>Delete</button></div></td></tr>)}
    </tbody></table>}

    {selectedId ? <div className='panel'>
      {readiness ? <div className='panel'>
        <h3>Cluster Readiness: <span style={{padding:'2px 8px', borderRadius:8, background:readinessBg, color:readinessTone}}>{readinessStatus || 'UNKNOWN'}</span></h3>
        {readinessStatus === 'WARN' ? <p style={{color:'#92400e', fontWeight:600}}>Balanced placement is constrained. Required assets are not available on every eligible node.</p> : null}
        {readinessStatus === 'FAIL' ? <p style={{color:'#991b1b', fontWeight:600}}>Cluster readiness has blocking failures.</p> : null}
        <div className='group' style={{alignItems:'flex-start'}}>
          <div><strong>Placement policy:</strong> {readiness?.defaults?.placement_policy || 'not set'}</div>
          <div><strong>Eligible nodes:</strong> {(readiness.eligible_nodes || []).join(', ') || 'none'}</div>
          <div><strong>Asset-ready nodes:</strong> {(readiness.asset_ready_nodes || []).join(', ') || 'none'}</div>
          <div><strong>Constrained nodes:</strong> {(readiness.constrained_nodes || []).join(', ') || 'none'}</div>
        </div>
        {(readiness.asset_ready_nodes || []).length === 1 && (readiness.constrained_nodes || []).length > 0 ? (
          <p className='muted'>
            Current cluster style indicates <strong>{readiness.asset_ready_nodes[0]}</strong> is asset-ready while constrained nodes should not be targeted for balanced provisioning until assets are shared, replicated, prepared, or placement is explicitly constrained.
          </p>
        ) : null}
        {(readiness.excluded_nodes || []).length ? <p className='muted'>Excluded nodes: {readiness.excluded_nodes.join(', ')}</p> : null}
        {readiness.excluded_node_reasons ? <ul>{Object.entries(readiness.excluded_node_reasons).map(([n,rs])=><li key={n} className='muted'>{n}: {(rs || []).join(', ')}</li>)}</ul> : null}
        {readiness.missing_templates_by_node ? <div>
          <h4>Missing Templates by Node</h4>
          {Object.keys(readiness.missing_templates_by_node).length === 0 ? <p className='muted'>No template gaps reported.</p> : (
            <table className='vm-table'>
              <thead><tr><th>Node</th><th>Missing template VMIDs</th></tr></thead>
              <tbody>
                {Object.entries(readiness.missing_templates_by_node).map(([node, missing])=>(
                  <tr key={node}><td>{node}</td><td>{(missing || []).join(', ') || '-'}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </div> : null}
        {readiness.missing_isos_by_node ? <div>
          <h4>Missing ISO/Media by Node</h4>
          {Object.keys(readiness.missing_isos_by_node).length === 0 ? <p className='muted'>No ISO/media gaps reported.</p> : (
            <table className='vm-table'>
              <thead><tr><th>Node</th><th>Missing ISO/media items</th></tr></thead>
              <tbody>
                {Object.entries(readiness.missing_isos_by_node).map(([node, missing])=>(
                  <tr key={node}><td>{node}</td><td>{(missing || []).join(', ') || '-'}</td></tr>
                ))}
              </tbody>
            </table>
          )}
        </div> : null}
        {(readiness.warnings || []).length ? <ul>{readiness.warnings.map((w,i)=><li key={i} className='muted'>{w}</li>)}</ul> : null}
        {(readiness.failures || []).length ? <ul>{readiness.failures.map((w,i)=><li key={i} className='muted'>{w}</li>)}</ul> : null}
        {(readiness.recommended_next_steps || []).length ? <div>
          <h4>Recommended Actions</h4>
          <ul>{readiness.recommended_next_steps.map((w,i)=><li key={i} className='muted'>{w}</li>)}</ul>
        </div> : null}
        <p className='muted'>Template/media sync automation may be unsupported. Use shared storage or manual Proxmox replication when guided below.</p>
        <button disabled={loading} onClick={()=>refreshDiscovery(selectedId)}>Refresh Readiness</button>
        <select className='input' value={selectedTemplateVmid} onChange={e=>setSelectedTemplateVmid(e.target.value)}>
          <option value=''>Select template for dry-run</option>
          {(templates || []).map((t,idx)=><option key={`${t.node}-${t.vmid}-${idx}`} value={t.vmid}>{t.vmid} - {t.name} ({t.node})</option>)}
        </select>
        <button disabled={loading || !selectedTemplateVmid} onClick={runTemplateSyncPlan}>Template Sync Plan (Dry-run)</button>
        <select className='input' value={selectedIsoId} onChange={e=>setSelectedIsoId(e.target.value)}>
          <option value=''>Select ISO/media for dry-run</option>
          {(readiness?.isos || []).map((i,idx)=><option key={`${i.node}-${i.storage}-${i.content_id||idx}`} value={i.content_id || i.name}>{i.name} ({i.node}/{i.storage})</option>)}
        </select>
        <button disabled={loading || !selectedIsoId} onClick={runIsoSyncPlan}>ISO Sync Plan (Dry-run)</button>
        {readiness?.isos?.length===0 ? <p className='muted'>ISO/media readiness: empty or unsupported in current cluster discovery.</p> : <p className='muted'>ISO/media discovered: {readiness.isos.length}</p>}
        {assetPlanMsg ? <pre className='muted' style={{whiteSpace:'pre-wrap'}}>{assetPlanMsg}</pre> : null}
      </div> : null}
      <h3>Defaults</h3>
      <p className='muted'>Default node = where new VMs are created unless placement policy selects another. Default storage = target storage for VM disks. Default bridge = VM network bridge. Default template VMID = template clone source.</p><p className='muted'>If resource data is unavailable, placement uses online node list with deterministic fallback rules.</p>
      <div className='group'>
        {nodes.length ? <select className='input' value={defaultsForm.default_node || ''} onChange={e=>setDefaultsForm({...defaultsForm,default_node:e.target.value})}><option value=''>Default node (optional)</option>{nodes.map(n=><option key={n.id} value={n.node_name}>{n.node_name}</option>)}</select> : <input className='input' placeholder='Default node' value={defaultsForm.default_node || ''} onChange={e=>setDefaultsForm({...defaultsForm,default_node:e.target.value})}/>}
        {storage.length ? <select className='input' value={defaultsForm.default_storage || ''} onChange={e=>setDefaultsForm({...defaultsForm,default_storage:e.target.value})}><option value=''>Default storage (optional)</option>{storage.map((s,idx)=><option key={`${s.node}-${s.storage}-${idx}`} value={s.storage}>{s.storage} ({s.node})</option>)}</select> : <input className='input' placeholder='Default storage' value={defaultsForm.default_storage || ''} onChange={e=>setDefaultsForm({...defaultsForm,default_storage:e.target.value})}/>}
        {networks.length ? <select className='input' value={defaultsForm.default_bridge || ''} onChange={e=>setDefaultsForm({...defaultsForm,default_bridge:e.target.value})}><option value=''>Default bridge (optional)</option>{networks.map((n,idx)=><option key={`${n.node}-${n.bridge}-${idx}`} value={n.bridge}>{n.bridge} ({n.node})</option>)}</select> : <input className='input' placeholder='Default bridge' value={defaultsForm.default_bridge || ''} onChange={e=>setDefaultsForm({...defaultsForm,default_bridge:e.target.value})}/>}
        {templates.length ? <select className='input' value={defaultsForm.default_template_vmid || ''} onChange={e=>setDefaultsForm({...defaultsForm,default_template_vmid:e.target.value})}><option value=''>Default template VMID (optional)</option>{templates.map((t,idx)=><option key={`${t.node}-${t.vmid}-${idx}`} value={t.vmid}>{t.vmid} - {t.name} ({t.node})</option>)}</select> : <input className='input' placeholder='Default template VMID' value={defaultsForm.default_template_vmid || ''} onChange={e=>setDefaultsForm({...defaultsForm,default_template_vmid:e.target.value})}/>}
        <select className='input' value={defaultsForm.clone_mode || 'full'} onChange={e=>setDefaultsForm({...defaultsForm,clone_mode:e.target.value})}><option value='full'>full</option><option value='linked'>linked</option></select>
        <select className='input' value={defaultsForm.placement_policy || ''} onChange={e=>setDefaultsForm({...defaultsForm,placement_policy:e.target.value})}><option value=''>Placement policy (auto)</option><option value='manual'>Manual/default node only</option><option value='balanced'>Balanced across online nodes</option><option value='prefer_default_then_balance'>Prefer default, fallback balanced</option></select>
        <input className='input' placeholder='Notes' value={defaultsForm.notes || ''} onChange={e=>setDefaultsForm({...defaultsForm,notes:e.target.value})}/>
        <button disabled={loading} onClick={()=>refreshDiscovery(selectedId)}>Refresh Discovery</button>
        <button disabled={loading} onClick={doSaveDefaults}>Save Defaults</button>
      </div>
      <div className='group'>
        <div><strong>Nodes:</strong> {nodes.length}</div>
        <div><strong>Storage targets:</strong> {storage.length}</div>
        <div><strong>Templates:</strong> {templates.length}</div>
        <div><strong>Bridges:</strong> {networks.length}</div>
      </div>
    </div> : null}

    {msg ? <p className='muted'>{msg}</p> : null}
  </section>
}
