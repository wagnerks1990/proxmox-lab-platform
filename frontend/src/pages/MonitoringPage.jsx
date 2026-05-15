import { useEffect, useState } from 'react'
import api from '../services/api'
import StatCard from '../components/StatCard'

export default function MonitoringPage() {
  const [s,setS]=useState(null)
  useEffect(()=>{api.get('/admin/monitoring/summary').then(r=>setS(r.data)).catch(()=>setS(null))},[])
  if(!s) return <section className='panel'><h2>Monitoring</h2><p className='muted'>Unavailable.</p></section>
  return <section className='panel'><h2>Monitoring</h2><div className='cards6'><StatCard label='Total VMs' value={s.total_vms}/><StatCard label='Running' value={s.running_vms}/><StatCard label='Stopped' value={s.stopped_vms}/><StatCard label='Recent Sessions' value={s.recent_sessions}/><StatCard label='Failed Actions' value={s.failed_actions}/><StatCard label='Proxmox Health' value={String(s.proxmox_health)}/></div></section>
}
