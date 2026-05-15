import { useEffect, useMemo, useState } from 'react'
import api from '../services/api'
import StatCard from '../components/StatCard'
import ActivityFeed from '../components/ActivityFeed'
import HealthPanel from '../components/HealthPanel'

export default function DashboardPage({ user }) {
  const [vms, setVms] = useState([])
  const [templates, setTemplates] = useState([])
  const [activity, setActivity] = useState([])
  const [health, setHealth] = useState(null)

  useEffect(() => {
    api.get('/vms').then(r => setVms(r.data))
    api.get('/templates').then(r => setTemplates(r.data))
    api.get('/health').then(r => setHealth(r.data)).catch(() => setHealth(null))
    if (user?.role === 'Admin' || user?.role === 'Teacher') api.get('/admin/session-activity').then(r => setActivity(r.data.slice(0, 8))).catch(() => setActivity([]))
  }, [user])

  const stats = useMemo(() => ({
    total: vms.length,
    running: vms.filter(v => v.status === 'running').length,
    stopped: vms.filter(v => v.status === 'stopped').length,
    templates: templates.length,
    activeSessions: activity.filter(a => a.status === 'success').length,
    failedActions: activity.filter(a => a.status === 'failed').length,
  }), [vms, templates, activity])

  return <div className='grid-2'>
    <div className='panel'>
      <h2>Dashboard</h2>
      <div className='cards6'>
        <StatCard label='Total VMs' value={stats.total} />
        <StatCard label='Running' value={stats.running} />
        <StatCard label='Stopped' value={stats.stopped} />
        <StatCard label='Available Templates' value={stats.templates} />
        <StatCard label='Active Sessions' value={stats.activeSessions} />
        <StatCard label='Failed Actions' value={stats.failedActions} />
      </div>
      <div className='group' style={{ marginTop: 12 }}><button className='btn'>Quick: Create Lab</button><button className='btn ghost'>Quick: Refresh VMs</button></div>
    </div>
    <div className='stack'>
      <HealthPanel health={health} />
      <ActivityFeed rows={activity} />
    </div>
  </div>
}
