import { useEffect, useMemo, useState } from 'react'
import api from '../services/api'

export default function DashboardPage({ user }) {
  const [vms, setVms] = useState([])
  const [templates, setTemplates] = useState([])
  useEffect(() => { api.get('/vms').then(r => setVms(r.data)); api.get('/templates').then(r => setTemplates(r.data)) }, [])
  const stats = useMemo(() => ({ total: vms.length, running: vms.filter(v=>v.status==='running').length, stopped: vms.filter(v=>v.status==='stopped').length, templates: templates.length }), [vms, templates])
  return <div><h2>{user.role} Dashboard</h2><div style={{display:'grid',gridTemplateColumns:'repeat(4,minmax(140px,1fr))',gap:10}}>{Object.entries(stats).map(([k,v])=><div key={k} style={{border:'1px solid #ddd',borderRadius:8,padding:12}}><div>{k}</div><strong>{v}</strong></div>)}</div></div>
}
