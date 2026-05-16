import { useEffect, useState } from 'react'
import api from '../services/api'

export default function ProxmoxPage({ setMessage }) {
  const [clusters,setClusters]=useState([])
  const [nodes,setNodes]=useState([])
  const [cform,setCform]=useState({name:'',api_url:'',enabled:true,description:''})
  const load=()=>{api.get('/admin/proxmox/clusters').then(r=>setClusters(r.data)); api.get('/admin/proxmox/nodes').then(r=>setNodes(r.data))}
  useEffect(()=>{load()},[])
  const create=async()=>{try{await api.post('/admin/proxmox/clusters',cform);load()}catch{setMessage({type:'error',text:'Create cluster failed'})}}
  const sync=async()=>{try{await api.post('/admin/proxmox/nodes/sync');load()}catch{setMessage({type:'error',text:'Node sync failed'})}}
  return <section className='grid-2'><div className='panel'><h2>Proxmox Clusters</h2><div className='group'><input className='input' placeholder='Name' value={cform.name} onChange={e=>setCform({...cform,name:e.target.value})}/><input className='input' placeholder='API URL' value={cform.api_url} onChange={e=>setCform({...cform,api_url:e.target.value})}/><button className='btn' onClick={create}>Add Cluster</button></div><table className='table2'><thead><tr><th>Name</th><th>API</th><th>Enabled</th><th>Description</th></tr></thead><tbody>{clusters.map(c=><tr key={c.id}><td>{c.name}</td><td>{c.api_url}</td><td>{String(c.enabled)}</td><td>{c.description||'-'}</td></tr>)}</tbody></table></div><div className='panel'><div className='panel-head'><h2>Proxmox Nodes</h2><button className='btn' onClick={sync}>Sync Nodes</button></div><table className='table2'><thead><tr><th>Node</th><th>Cluster</th><th>Status</th><th>CPU</th><th>Memory</th></tr></thead><tbody>{nodes.map(n=><tr key={n.id}><td>{n.node_name}</td><td>{n.cluster_id}</td><td>{n.status||'-'}</td><td>{n.cpu_usage||'-'}</td><td>{n.memory_usage||'-'}</td></tr>)}</tbody></table></div></section>
}
