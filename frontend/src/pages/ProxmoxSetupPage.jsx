import { useEffect, useState } from 'react'
import api from '../services/api'

const defaultBootstrap = { name:'Primary Proxmox', api_url:'', verify_ssl:false, root_username:'root@pam', root_password:'', token_id:'proxmox-lab-platform' }
const defaultManual = { name:'Primary Proxmox', api_url:'', verify_ssl:false, token_user:'root@pam', token_id:'proxmox-lab-platform', token_secret:'' }
const defaultDefaults = { default_node:'', default_storage:'', default_bridge:'', default_template_vmid:'', clone_mode:'full', notes:'' }

export default function ProxmoxSetupPage(){
  const [clusters,setClusters]=useState([])
  const [loading,setLoading]=useState(false)
  const [msg,setMsg]=useState('')
  const [bootstrap,setBootstrap]=useState(defaultBootstrap)
  const [manual,setManual]=useState(defaultManual)
  const [defaultsForm,setDefaultsForm]=useState(defaultDefaults)
  const [selectedId,setSelectedId]=useState(null)
  const [nodes,setNodes]=useState([])

  const load = async ()=>{
    const {data} = await api.get('/admin/proxmox/clusters')
    setClusters(Array.isArray(data)?data:[])
  }
  useEffect(()=>{load().catch(()=>setClusters([]))},[])

  const run = async (fn)=>{ setLoading(true); setMsg(''); try{ await fn() } catch(e){ setMsg(JSON.stringify(e?.response?.data?.detail || e?.response?.data || e.message)) } finally { setLoading(false) } }

  const doBootstrap = ()=> run(async ()=>{
    const {data} = await api.post('/admin/proxmox/bootstrap-root', bootstrap)
    if (data?.token_exists) {
      setMsg(`${data.message} Suggested: ${data.suggested_actions?.join(' | ')}`)
    } else {
      setMsg('Bootstrap successful.')
      setBootstrap({...bootstrap, root_password:''})
      await load()
    }
  })

  const doManual = ()=> run(async ()=>{
    await api.post('/admin/proxmox/clusters/manual-token', manual)
    setMsg('Manual token saved and validated.')
    setManual({...manual, token_secret:''})
    await load()
  })

  const doValidate = (id)=> run(async ()=>{ await api.post(`/admin/proxmox/clusters/${id}/validate`); setMsg('Validation complete.'); await load() })
  const doActivate = (id)=> run(async ()=>{ await api.post(`/admin/proxmox/clusters/${id}/activate`); setMsg('Cluster activated.'); await load() })
  const doDelete = (id)=> run(async ()=>{ if(!window.confirm('Delete app cluster record only?')) return; await api.delete(`/admin/proxmox/clusters/${id}`); setMsg('Cluster record deleted from app DB.'); if (selectedId===id) { setSelectedId(null); setNodes([]) } await load() })
  const doPatchCluster = (id, patch)=> run(async ()=>{ await api.patch(`/admin/proxmox/clusters/${id}`, patch); setMsg('Cluster updated.'); await load() })
  const doPatchDefaults = (id)=> run(async ()=>{ await api.patch(`/admin/proxmox/clusters/${id}/defaults`, { ...defaultsForm, default_template_vmid: defaultsForm.default_template_vmid ? Number(defaultsForm.default_template_vmid) : null }); setMsg('Defaults updated.'); await load() })
  const loadNodes = (id)=> run(async ()=>{ const {data}=await api.get(`/admin/proxmox/clusters/${id}/nodes`); setNodes(Array.isArray(data)?data:[]); setSelectedId(id) })

  return <section className='panel'>
    <h2>Proxmox Setup</h2>
    <p className='muted'>Root credentials are used only during bootstrap. Root password is never stored.</p>

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

    <h3>Manual Token</h3>
    <div className='group'>
      <input className='input' placeholder='Cluster name' value={manual.name} onChange={e=>setManual({...manual,name:e.target.value})}/>
      <input className='input' placeholder='API URL' value={manual.api_url} onChange={e=>setManual({...manual,api_url:e.target.value})}/>
      <input className='input' placeholder='Token user' value={manual.token_user} onChange={e=>setManual({...manual,token_user:e.target.value})}/>
      <input className='input' placeholder='Token ID' value={manual.token_id} onChange={e=>setManual({...manual,token_id:e.target.value})}/>
      <input className='input' type='password' placeholder='Token secret' value={manual.token_secret} onChange={e=>setManual({...manual,token_secret:e.target.value})}/>
      <label><input type='checkbox' checked={manual.verify_ssl} onChange={e=>setManual({...manual,verify_ssl:e.target.checked})}/> Verify SSL</label>
      <button disabled={loading} onClick={doManual}>Save Manual Token</button>
    </div>

    <h3>Configured Clusters</h3>
    {clusters.length===0 ? <p className='muted'>No clusters configured yet.</p> : <table className='vm-table'><thead><tr><th>Name</th><th>URL</th><th>Token</th><th>Active</th><th>Validation</th><th>Actions</th></tr></thead><tbody>{clusters.map(c=><tr key={c.id}><td>{c.name}</td><td>{c.api_url}</td><td>{c.token_user} / {c.token_id}</td><td>{String(c.is_active)}</td><td>{c.last_validation_status||'-'} {c.last_validated_at||''}</td><td><div className='group'><button disabled={loading} onClick={()=>doValidate(c.id)}>Validate</button><button disabled={loading} onClick={()=>doActivate(c.id)}>Activate</button><button disabled={loading} onClick={()=>loadNodes(c.id)}>Nodes</button><button disabled={loading} onClick={()=>doPatchCluster(c.id,{verify_ssl:!c.verify_ssl})}>Toggle SSL</button><button disabled={loading} onClick={()=>doDelete(c.id)}>Delete</button></div></td></tr>)}</tbody></table>}

    {selectedId ? <div className='panel'><h4>Defaults (Cluster {selectedId})</h4><div className='group'>
      <input className='input' placeholder='Default node' value={defaultsForm.default_node} onChange={e=>setDefaultsForm({...defaultsForm,default_node:e.target.value})}/>
      <input className='input' placeholder='Default storage' value={defaultsForm.default_storage} onChange={e=>setDefaultsForm({...defaultsForm,default_storage:e.target.value})}/>
      <input className='input' placeholder='Default bridge' value={defaultsForm.default_bridge} onChange={e=>setDefaultsForm({...defaultsForm,default_bridge:e.target.value})}/>
      <input className='input' placeholder='Default template VMID' value={defaultsForm.default_template_vmid} onChange={e=>setDefaultsForm({...defaultsForm,default_template_vmid:e.target.value})}/>
      <input className='input' placeholder='Clone mode' value={defaultsForm.clone_mode} onChange={e=>setDefaultsForm({...defaultsForm,clone_mode:e.target.value})}/>
      <input className='input' placeholder='Notes' value={defaultsForm.notes} onChange={e=>setDefaultsForm({...defaultsForm,notes:e.target.value})}/>
      <button disabled={loading} onClick={()=>doPatchDefaults(selectedId)}>Save Defaults</button>
    </div>
    <h5>Discovered Nodes</h5>
    {nodes.length===0 ? <p className='muted'>No nodes loaded yet.</p> : <ul>{nodes.map(n=><li key={n.id}>{n.node_name} ({n.status||'unknown'})</li>)}</ul>}
    </div> : null}

    {msg ? <p className='muted'>{msg}</p> : null}
  </section>
}
