import { useEffect, useState } from 'react'
import api from '../services/api'
import StatCard from '../components/StatCard'

export default function MonitoringPage() {
  const [s,setS]=useState(null)
  useEffect(()=>{api.get('/admin/monitoring/summary').then(r=>setS(r.data)).catch(()=>setS(null))},[])
  if(!s) return <section className='panel'><h2>Monitoring</h2><p className='muted'>Unavailable.</p></section>
  return <section className='panel'><h2>Monitoring</h2><div className='cards6'><StatCard label='Total VMs' value={s.total_vms}/><StatCard label='Running' value={s.running_vms}/><StatCard label='Stopped' value={s.stopped_vms}/><StatCard label='Recent Sessions' value={s.recent_sessions}/><StatCard label='Failed Actions' value={s.failed_actions}/><StatCard label='Proxmox Health' value={String(s.proxmox_health)}/></div><div className='panel' style={{marginTop:12}}><h4>Cluster Health</h4><div className='group'>{(s.cluster_health||[]).map((c,i)=><div key={i} className='mini-card'>{c.cluster}: {String(c.enabled)}</div>)}</div></div><div className='panel' style={{marginTop:12}}><h4>Node Health</h4><table className='table2'><thead><tr><th>Node</th><th>Status</th><th>VMs</th><th>Running</th><th>CPU</th><th>Memory</th></tr></thead><tbody>{(s.node_health||[]).map((n,i)=><tr key={i}><td>{n.node}</td><td>{n.status||'-'}</td><td>{n.vm_count}</td><td>{n.running_vm_count}</td><td>{n.cpu_usage||'-'}</td><td>{n.memory_usage||'-'}</td></tr>)}</tbody></table></div></section>
}
