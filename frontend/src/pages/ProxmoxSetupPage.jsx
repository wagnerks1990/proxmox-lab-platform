import { useEffect, useMemo, useState } from 'react'
import api from '../services/api'

const bootstrapInit = { name:'Primary Proxmox', api_url:'', verify_ssl:true, root_password:'' }
const manualInit = { name:'Primary Proxmox', api_url:'', verify_ssl:true, token_user:'labgoblin@pve', token_id:'labgoblin', token_secret:'' }
const defaultsInit = { default_node:'', default_storage:'', default_bridge:'', default_template_vmid:'', clone_mode:'full', placement_policy:'', notes:'' }
const statusTone = status => status === 'PASS' || status === 'ok' ? 'ui-status-badge--success' : status === 'WARN' ? 'ui-status-badge--warning' : status === 'FAIL' ? 'ui-status-badge--danger' : 'ui-status-badge--neutral'

export default function ProxmoxSetupPage(){
  const secureBootstrapContext = window.isSecureContext
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

  // A saved connection remains active after navigation, but its discovery data is
  // intentionally kept only in client state. Reload it for the active cluster so
  // the Defaults editor is available immediately after returning to this page.
  useEffect(()=>{
    if (activeCluster?.id && selectedId !== activeCluster.id) {
      refreshDiscovery(activeCluster.id)
    }
  }, [activeCluster?.id])

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
    const {data} = await api.post('/admin/proxmox/bootstrap-root', { ...bootstrap, root_username:'root@pam' })
    setBootstrap({...bootstrap, root_password:''})
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

  return <section className='page-shell' aria-labelledby='proxmox-setup-title'>
    <header className='ui-page-header'><div className='ui-page-header__copy'><p className='muted'>Infrastructure</p><h2 id='proxmox-setup-title' className='ui-page-header__title'>Proxmox setup</h2><p className='ui-page-header__description'>Connect clusters, validate access, review readiness, and set placement defaults.</p></div></header>
    {activeCluster ? <p className='ui-alert ui-alert--success'><strong>Active cluster:</strong>&nbsp; {activeCluster.name} ({activeCluster.api_url})</p> : <p className='ui-alert ui-alert--warning'>No active cluster is configured.</p>}
    <p className='muted'>Root credentials are used once to create the dedicated labgoblin@pve account, LabGoblinRole permissions, and labgoblin API token. The root password is never stored. The generated token secret is encrypted at rest and never returned by the API.</p>

    <button disabled={loading} aria-expanded={showBootstrap || !activeCluster} aria-controls='cluster-connection-forms' onClick={()=>setShowBootstrap(!showBootstrap)}>{showBootstrap ? 'Hide connection forms' : 'Add or reconnect cluster'}</button>

    {(showBootstrap || !activeCluster) ? <section id='cluster-connection-forms' className='ui-card'>
      <h3>Automatic dedicated access</h3>
      <p className='muted'>Use this only from an HTTPS page or a localhost SSH tunnel. Existing users or roles with conflicting permissions are not overwritten.</p>
      {!secureBootstrapContext ? <p className='ui-alert ui-alert--error' role='alert'>Root bootstrap is blocked on an insecure browser connection. Use HTTPS or open LabGoblin through a localhost SSH tunnel.</p> : null}
      <div className='ui-form-grid'>
        <label className='ui-field'>Cluster name<input className='input' value={bootstrap.name} onChange={e=>setBootstrap({...bootstrap,name:e.target.value})}/></label>
        <label className='ui-field'>API URL<input className='input' type='url' value={bootstrap.api_url} onChange={e=>setBootstrap({...bootstrap,api_url:e.target.value})}/></label>
        <div className='ui-field'><span>Dedicated identity</span><strong>labgoblin@pve!labgoblin</strong></div>
        <label className='ui-field'>Root password<input className='input' type='password' autoComplete='off' value={bootstrap.root_password} onChange={e=>setBootstrap({...bootstrap,root_password:e.target.value})}/></label>
        <label><input type='checkbox' checked={bootstrap.verify_ssl} onChange={e=>setBootstrap({...bootstrap,verify_ssl:e.target.checked})}/> Verify SSL</label>
        <button disabled={loading || !secureBootstrapContext} onClick={doBootstrap}>Create dedicated Proxmox access</button>
      </div>
      <h3>Host access</h3>
      <p className='muted'>Current mode: {hostAccess?.mode || 'api_only'}. Root password is used only during this request and is not persisted.</p>
      {hostAccess?.mode === 'static_asset_server' ? <div className='panel'><p className='muted'>Static asset server mode is active. ISO/CT source URLs can be generated.</p><p className='muted'>Host-runner command execution is disabled.</p><p className='muted'>Root password is not used in this mode.</p></div> : null}
      <div className='group'>
        {hostAccess?.mode !== 'static_asset_server' ? <>
          <label className='ui-field'>Root username<input className='input' value={hostAccessForm.root_username} onChange={e=>setHostAccessForm({...hostAccessForm, root_username:e.target.value})}/></label>
          <label className='ui-field'>One-time root password<input className='input' type='password' autoComplete='off' value={hostAccessForm.root_password} onChange={e=>setHostAccessForm({...hostAccessForm, root_password:e.target.value})}/></label>
          <label className='ui-field'>Target nodes<select className='input' multiple value={hostAccessForm.node_names} onChange={e=>setHostAccessForm({...hostAccessForm, node_names:[...e.target.selectedOptions].map(o=>o.value)})}>
            {(hostAccess?.nodes || nodes).map(n => <option key={n.node_name} value={n.node_name}>{n.node_name}</option>)}
          </select></label>
        </> : null}
        <button disabled={true} title='Host runner bootstrap is not enabled/configured yet.' onClick={bootstrapHostAccess}>Configure Host Runner</button>
        <button disabled={loading || !(selectedId || activeCluster?.id)} onClick={validateHostAccess}>Validate Host Access</button>
      </div>
      <p className='muted'>Host runner bootstrap is not enabled/configured yet.</p>
      {hostAccessResult ? <p className={`ui-alert ${hostAccessResult.ok ? 'ui-alert--success' : 'ui-alert--error'}`} role={hostAccessResult.ok?'status':'alert'}><strong>Host access result:</strong>&nbsp; {hostAccessResult.message}</p> : null}
      <h3>Manual token fallback</h3>
      <div className='ui-form-grid'>
        <label className='ui-field'>Cluster name<input className='input' value={manual.name} onChange={e=>setManual({...manual,name:e.target.value})}/></label>
        <label className='ui-field'>API URL<input className='input' type='url' value={manual.api_url} onChange={e=>setManual({...manual,api_url:e.target.value})}/></label>
        <label className='ui-field'>Token user<input className='input' value={manual.token_user} onChange={e=>setManual({...manual,token_user:e.target.value})}/></label>
        <label className='ui-field'>Token ID<input className='input' value={manual.token_id} onChange={e=>setManual({...manual,token_id:e.target.value})}/></label>
        <label className='ui-field'>Token secret<input className='input' type='password' autoComplete='off' value={manual.token_secret} onChange={e=>setManual({...manual,token_secret:e.target.value})}/></label>
        <label><input type='checkbox' checked={manual.verify_ssl} onChange={e=>setManual({...manual,verify_ssl:e.target.checked})}/> Verify SSL</label>
        <button disabled={loading} onClick={doManualToken}>Save Manual Token</button>
      </div>
    </section> : null}

    <section className='ui-card' aria-labelledby='configured-clusters-title'><h3 id='configured-clusters-title'>Configured clusters</h3>
    {clusters.length===0 ? <p className='muted'>No clusters configured yet.</p> : <div className='ui-table-wrap' role='region' aria-labelledby='configured-clusters-title' tabIndex='0'><table className='ui-table'><thead><tr><th scope='col'>Name</th><th scope='col'>API URL</th><th scope='col'>Token</th><th scope='col'>Active</th><th scope='col'>Validation</th><th scope='col'>Actions</th></tr></thead><tbody>
      {clusters.map(c=><tr key={c.id}><th scope='row'>{c.name}</th><td>{c.api_url}</td><td>{c.token_user} / {c.token_id}</td><td>{c.is_active?'Yes':'No'}</td><td><span className={`ui-status-badge ${statusTone(c.last_validation_status)}`}>{c.last_validation_status || 'Not validated'}</span> {c.last_validated_at || ''}</td><td><div className='ui-cluster'><button disabled={loading} aria-label={`Validate cluster ${c.name}`} onClick={()=>doValidate(c.id)}>Validate</button><button disabled={loading} aria-label={`Activate cluster ${c.name}`} onClick={()=>doActivate(c.id)}>Activate</button><button disabled={loading} aria-label={`Refresh discovery for ${c.name}`} onClick={()=>refreshDiscovery(c.id)}>Refresh discovery</button><button className='ui-button--danger' disabled={loading} aria-label={`Delete cluster record ${c.name}`} onClick={()=>doDelete(c.id)}>Delete</button></div></td></tr>)}
    </tbody></table></div>}
    </section>

    {selectedId ? <div className='panel'>
      {readiness ? <div className='panel'>
        <h3>Cluster readiness: <span className={`ui-status-badge ${statusTone(readinessStatus)}`}>{readinessStatus || 'UNKNOWN'}</span></h3>
        {readinessStatus === 'WARN' ? <p className='ui-alert ui-alert--warning'>Balanced placement is constrained. Required assets are not available on every eligible node.</p> : null}
        {readinessStatus === 'FAIL' ? <p className='ui-alert ui-alert--error'>Cluster readiness has blocking failures.</p> : null}
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
            <div className='ui-table-wrap' role='region' aria-label='Missing templates by node' tabIndex='0'><table className='ui-table'>
              <thead><tr><th scope='col'>Node</th><th scope='col'>Missing template VMIDs</th></tr></thead>
              <tbody>
                {Object.entries(readiness.missing_templates_by_node).map(([node, missing])=>(
                  <tr key={node}><td>{node}</td><td>{(missing || []).join(', ') || '-'}</td></tr>
                ))}
              </tbody>
            </table></div>
          )}
        </div> : null}
        {readiness.missing_isos_by_node ? <div>
          <h4>Missing ISO/Media by Node</h4>
          {Object.keys(readiness.missing_isos_by_node).length === 0 ? <p className='muted'>No ISO/media gaps reported.</p> : (
            <div className='ui-table-wrap' role='region' aria-label='Missing media by node' tabIndex='0'><table className='ui-table'>
              <thead><tr><th scope='col'>Node</th><th scope='col'>Missing ISO/media items</th></tr></thead>
              <tbody>
                {Object.entries(readiness.missing_isos_by_node).map(([node, missing])=>(
                  <tr key={node}><td>{node}</td><td>{(missing || []).join(', ') || '-'}</td></tr>
                ))}
              </tbody>
            </table></div>
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
        <label className='ui-field'>Template for dry-run<select className='input' value={selectedTemplateVmid} onChange={e=>setSelectedTemplateVmid(e.target.value)}>
          <option value=''>Select template for dry-run</option>
          {(templates || []).map((t,idx)=><option key={`${t.node}-${t.vmid}-${idx}`} value={t.vmid}>{t.vmid} - {t.name} ({t.node})</option>)}
        </select></label>
        <button disabled={loading || !selectedTemplateVmid} onClick={runTemplateSyncPlan}>Template Sync Plan (Dry-run)</button>
        <label className='ui-field'>ISO or media for dry-run<select className='input' value={selectedIsoId} onChange={e=>setSelectedIsoId(e.target.value)}>
          <option value=''>Select ISO/media for dry-run</option>
          {(readiness?.isos || []).map((i,idx)=><option key={`${i.node}-${i.storage}-${i.content_id||idx}`} value={i.content_id || i.name}>{i.name} ({i.node}/{i.storage})</option>)}
        </select></label>
        <button disabled={loading || !selectedIsoId} onClick={runIsoSyncPlan}>ISO Sync Plan (Dry-run)</button>
        {readiness?.isos?.length===0 ? <p className='muted'>ISO/media readiness: empty or unsupported in current cluster discovery.</p> : <p className='muted'>ISO/media discovered: {readiness.isos.length}</p>}
        {assetPlanMsg ? <pre className='muted' style={{whiteSpace:'pre-wrap'}}>{assetPlanMsg}</pre> : null}
      </div> : null}
      <h3>Defaults</h3>
      <p className='muted'>Default node = where new VMs are created unless placement policy selects another. Default storage = target storage for VM disks. Default bridge = VM network bridge. Default template VMID = template clone source.</p><p className='muted'>If resource data is unavailable, placement uses online node list with deterministic fallback rules.</p>
      <div className='ui-form-grid'>
        <label className='ui-field'>Default node (optional){nodes.length ? <select className='input' value={defaultsForm.default_node || ''} onChange={e=>setDefaultsForm({...defaultsForm,default_node:e.target.value})}><option value=''>Automatic selection</option>{nodes.map(n=><option key={n.id} value={n.node_name}>{n.node_name}</option>)}</select> : <input className='input' value={defaultsForm.default_node || ''} onChange={e=>setDefaultsForm({...defaultsForm,default_node:e.target.value})}/>}</label>
        <label className='ui-field'>Default storage (optional){storage.length ? <select className='input' value={defaultsForm.default_storage || ''} onChange={e=>setDefaultsForm({...defaultsForm,default_storage:e.target.value})}><option value=''>Automatic selection</option>{storage.map((s,idx)=><option key={`${s.node}-${s.storage}-${idx}`} value={s.storage}>{s.storage} ({s.node})</option>)}</select> : <input className='input' value={defaultsForm.default_storage || ''} onChange={e=>setDefaultsForm({...defaultsForm,default_storage:e.target.value})}/>}</label>
        <label className='ui-field'>Default bridge (optional){networks.length ? <select className='input' value={defaultsForm.default_bridge || ''} onChange={e=>setDefaultsForm({...defaultsForm,default_bridge:e.target.value})}><option value=''>Automatic selection</option>{networks.map((n,idx)=><option key={`${n.node}-${n.bridge}-${idx}`} value={n.bridge}>{n.bridge} ({n.node})</option>)}</select> : <input className='input' value={defaultsForm.default_bridge || ''} onChange={e=>setDefaultsForm({...defaultsForm,default_bridge:e.target.value})}/>}</label>
        <label className='ui-field'>Default template VMID (optional){templates.length ? <select className='input' value={defaultsForm.default_template_vmid || ''} onChange={e=>setDefaultsForm({...defaultsForm,default_template_vmid:e.target.value})}><option value=''>No default template</option>{templates.map((t,idx)=><option key={`${t.node}-${t.vmid}-${idx}`} value={t.vmid}>{t.vmid} - {t.name} ({t.node})</option>)}</select> : <input className='input' inputMode='numeric' value={defaultsForm.default_template_vmid || ''} onChange={e=>setDefaultsForm({...defaultsForm,default_template_vmid:e.target.value})}/>}</label>
        <label className='ui-field'>Clone mode<select className='input' value={defaultsForm.clone_mode || 'full'} onChange={e=>setDefaultsForm({...defaultsForm,clone_mode:e.target.value})}><option value='full'>Full clone</option><option value='linked'>Linked clone</option></select></label>
        <label className='ui-field'>Placement policy<select className='input' value={defaultsForm.placement_policy || ''} onChange={e=>setDefaultsForm({...defaultsForm,placement_policy:e.target.value})}><option value=''>Automatic</option><option value='manual'>Manual/default node only</option><option value='balanced'>Balanced across online nodes</option><option value='prefer_default_then_balance'>Prefer default, fallback balanced</option></select></label>
        <label className='ui-field ui-form-grid__wide'>Notes<input className='input' value={defaultsForm.notes || ''} onChange={e=>setDefaultsForm({...defaultsForm,notes:e.target.value})}/></label>
        <div className='ui-cluster ui-form-grid__wide'>
        <button disabled={loading} onClick={()=>refreshDiscovery(selectedId)}>Refresh Discovery</button>
        <button disabled={loading} onClick={doSaveDefaults}>Save Defaults</button>
        </div>
      </div>
      <div className='group'>
        <div><strong>Nodes:</strong> {nodes.length}</div>
        <div><strong>Storage targets:</strong> {storage.length}</div>
        <div><strong>Templates:</strong> {templates.length}</div>
        <div><strong>Bridges:</strong> {networks.length}</div>
      </div>
    </div> : null}

    {msg ? <p className='ui-alert' role='status' aria-live='polite'>{msg}</p> : null}
  </section>
}
