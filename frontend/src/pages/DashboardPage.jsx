import { useEffect, useMemo, useState } from 'react'
import api from '../services/api'

export default function DashboardPage({ user }) {
  const [vms, setVms] = useState([])
  const [templates, setTemplates] = useState([])
  useEffect(() => { api.get('/vms').then(r => setVms(r.data)); api.get('/templates').then(r => setTemplates(r.data)) }, [])
  const stats = useMemo(() => ({ total: vms.length, running: vms.filter(v=>v.status==='running').length, stopped: vms.filter(v=>v.status==='stopped').length, templates: templates.length }), [vms, templates])
  return <div><h2>{user.role} Dashboard</h2><div className='card-grid'>{Object.entries(stats).map(([k,v])=><div key={k} className='stat-card'><div className='label'>{k.toUpperCase()}</div><div className='value'>{v}</div></div>)}</div></div>
}
