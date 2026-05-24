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

  const activeCluster = useMemo(()=>clusters.find(c=>c.is_active),[clusters])

  const run = async (fn)=>{ setLoading(true); setMsg(''); try{ await fn() } catch(e){ setMsg(JSON.stringify(e?.response?.data?.detail || e?.response?.data || e.message)) } finally { setLoading(false) } }
  const loadClusters = async ()=>{ const {data} = await api.get('/admin/proxmox/clusters'); setClusters(Array.isArray(data)?data:[]) }

  useEffect(()=>{ loadClusters().catch(()=>setClusters([])) },[])

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
    setDefaultsForm({ ...defaultsInit, ...(cfg.data?.defaults || {}) })
    setMsg('Discovery refreshed.')
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
    const payload = { type:'template', template_vmid: defaultsForm.default_template_vmid ? Number(defaultsForm.default_template_vmid) : null, source_node: defaultsForm.default_node || null, target_nodes: nodes.map(n=>n.node_name).filter(n=>n!==defaultsForm.default_node), target_storage: defaultsForm.default_storage || null }
    const { data } = await api.post('/admin/proxmox/assets/sync-plan', payload)
    setAssetPlanMsg(JSON.stringify(data))
  })
  const runIsoSyncPlan = ()=>run(async ()=>{
    const payload = { type:'iso', source_node: defaultsForm.default_node || null, source_storage: defaultsForm.default_storage || null, volume: null, target_nodes: nodes.map(n=>n.node_name).filter(n=>n!==defaultsForm.default_node), target_storage: defaultsForm.default_storage || null }
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
        <h3>Cluster Readiness: {readiness.status}</h3>
        <p className='muted'>Eligible nodes: {(readiness.eligible_nodes || []).join(', ') || 'none'}</p>
        {(readiness.excluded_nodes || []).length ? <p className='muted'>Excluded nodes: {readiness.excluded_nodes.join(', ')}</p> : null}
        {readiness.excluded_node_reasons ? <ul>{Object.entries(readiness.excluded_node_reasons).map(([n,rs])=><li key={n} className='muted'>{n}: {(rs || []).join(', ')}</li>)}</ul> : null}
        {(readiness.warnings || []).length ? <ul>{readiness.warnings.map((w,i)=><li key={i} className='muted'>{w}</li>)}</ul> : null}
        {(readiness.failures || []).length ? <ul>{readiness.failures.map((w,i)=><li key={i} className='muted'>{w}</li>)}</ul> : null}
        {(readiness.recommended_next_steps || []).length ? <ul>{readiness.recommended_next_steps.map((w,i)=><li key={i} className='muted'>{w}</li>)}</ul> : null}
        <p className='muted'>Template/media sync automation may be unsupported. Use shared storage or manual Proxmox replication when guided below.</p>
        <button disabled={loading} onClick={()=>refreshDiscovery(selectedId)}>Refresh Readiness</button>
        <button disabled={loading} onClick={runTemplateSyncPlan}>Template Sync Plan (Dry-run)</button>
        <button disabled={loading} onClick={runIsoSyncPlan}>ISO Sync Plan (Dry-run)</button>
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
