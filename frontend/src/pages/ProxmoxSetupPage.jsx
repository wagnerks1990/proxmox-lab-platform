import { useEffect, useState } from 'react'
import api from '../services/api'

export default function ProxmoxSetupPage(){
  const [clusters,setClusters]=useState([])
  const [step,setStep]=useState(1)
  const [selected,setSelected]=useState(null)
  const [status,setStatus]=useState('')
  const [f,setF]=useState({name:'Primary Proxmox',api_url:'',verify_ssl:false,root_username:'root@pam',root_password:'',default_node:'',default_storage:'',default_bridge:'',default_template_vmid:'',clone_mode:'full'})

  const load = ()=> api.get('/admin/proxmox/clusters').then(r=>setClusters(Array.isArray(r.data)?r.data:[])).catch(()=>setClusters([]))
  useEffect(()=>{load()},[])

  const bootstrap = async ()=>{
    setStatus('Bootstrapping and validating...')
    try{
      const {data} = await api.post('/admin/proxmox/bootstrap-root', f)
      setSelected(data)
      setStatus('Bootstrap successful. Root password discarded; token stored securely.')
      setStep(4)
      load()
    }catch(e){
      setStatus(`Bootstrap failed: ${JSON.stringify(e?.response?.data?.detail || e.message)}`)
    }
  }

  const saveDefaults = async ()=>{
    if (!selected?.cluster_id) return
    await api.patch(`/admin/proxmox/clusters/${selected.cluster_id}/defaults`, {
      default_node:f.default_node || null,
      default_storage:f.default_storage || null,
      default_bridge:f.default_bridge || null,
      default_template_vmid:f.default_template_vmid ? Number(f.default_template_vmid) : null,
      clone_mode:f.clone_mode || null,
    })
    setStep(5)
    setStatus('Defaults saved. Ready to activate cluster.')
  }

  const activate = async ()=>{
    if (!selected?.cluster_id) return
    await api.post(`/admin/proxmox/clusters/${selected.cluster_id}/activate`)
    setStatus('Cluster activated. Proxmox runtime now prefers database config over .env fallback.')
    load()
  }

  return <section className='panel'>
    <h2>Proxmox Setup Wizard</h2>
    <p className='muted'>Root credentials are used only once to bootstrap a managed API token. Root password is not stored.</p>
    <p className='muted'>Current step: {step}</p>
    <div className='group'>
      <input className='input' placeholder='Setup name' value={f.name} onChange={e=>setF({...f,name:e.target.value})}/>
      <input className='input' placeholder='API URL (https://host:8006/api2/json)' value={f.api_url} onChange={e=>setF({...f,api_url:e.target.value})}/>
      <label><input type='checkbox' checked={f.verify_ssl} onChange={e=>setF({...f,verify_ssl:e.target.checked})}/> Verify SSL</label>
      <input className='input' placeholder='Root username' value={f.root_username} onChange={e=>setF({...f,root_username:e.target.value})}/>
      <input className='input' type='password' placeholder='Root password' value={f.root_password} onChange={e=>setF({...f,root_password:e.target.value})}/>
      <button onClick={bootstrap}>Bootstrap & Validate</button>
    </div>
    {selected ? <div className='panel'><h4>Bootstrap result</h4><div>Cluster: {selected.name}</div><div>Token User: {selected.token_user}</div><div>Token ID: {selected.token_id}</div><div>Nodes discovered: {selected.nodes_discovered}</div></div> : null}
    {selected ? <div className='group'>
      <input className='input' placeholder='Default node' value={f.default_node} onChange={e=>setF({...f,default_node:e.target.value})}/>
      <input className='input' placeholder='Default storage' value={f.default_storage} onChange={e=>setF({...f,default_storage:e.target.value})}/>
      <input className='input' placeholder='Default bridge' value={f.default_bridge} onChange={e=>setF({...f,default_bridge:e.target.value})}/>
      <input className='input' placeholder='Default template VMID' value={f.default_template_vmid} onChange={e=>setF({...f,default_template_vmid:e.target.value})}/>
      <input className='input' placeholder='Clone mode' value={f.clone_mode} onChange={e=>setF({...f,clone_mode:e.target.value})}/>
      <button onClick={saveDefaults}>Save Defaults</button>
      <button onClick={activate}>Activate Cluster</button>
    </div> : null}

    <h3>Configured Clusters</h3>
    {clusters.length===0 ? <p className='muted'>No configured clusters yet.</p> : <table className='vm-table'><thead><tr><th>Name</th><th>URL</th><th>Token</th><th>Active</th><th>Last Validation</th></tr></thead><tbody>{clusters.map(c=><tr key={c.id}><td>{c.name}</td><td>{c.api_url}</td><td>{c.token_user} / {c.token_id}</td><td>{String(c.is_active)}</td><td>{c.last_validation_status || '-'} {c.last_validated_at || ''}</td></tr>)}</tbody></table>}
    {status ? <p className='muted'>{status}</p> : null}
  </section>
}
