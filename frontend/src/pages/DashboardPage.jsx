import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../services/api'

function formatBytes(v){
  if (v === null || v === undefined) return '—'
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  if (n < 1024) return `${n} B`
  const units = ['KB','MB','GB','TB']
  let x = n / 1024
  let i = 0
  while (x >= 1024 && i < units.length - 1) { x /= 1024; i += 1 }
  return `${x.toFixed(1)} ${units[i]}`
}

function formatPct(v){
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '—'
  return `${Number(v).toFixed(1)}%`
}

function formatUptime(sec){
  if (!sec && sec !== 0) return '—'
  const s = Number(sec)
  const d = Math.floor(s / 86400)
  const h = Math.floor((s % 86400) / 3600)
  const m = Math.floor((s % 3600) / 60)
  return `${d}d ${h}h ${m}m`
}

export default function DashboardPage({ user }) {
  const [vms, setVms] = useState([])
  const [templates, setTemplates] = useState([])
  const [resourceStats, setResourceStats] = useState(null)
  const [loadingStats, setLoadingStats] = useState(false)
  const [statsError, setStatsError] = useState('')

  const loadTop = async () => {
    const [v, t] = await Promise.all([api.get('/vms'), api.get('/templates')])
    setVms(Array.isArray(v.data) ? v.data : [])
    setTemplates(Array.isArray(t.data) ? t.data : [])
  }

  const loadResourceStats = async () => {
    setLoadingStats(true)
    setStatsError('')
    try {
      const r = await api.get('/admin/proxmox/resource-stats')
      setResourceStats(r.data)
    } catch (e) {
      setStatsError(JSON.stringify(e?.response?.data?.detail || e?.response?.data || e.message))
    } finally {
      setLoadingStats(false)
    }
  }

  useEffect(() => {
    loadTop().catch(() => {})
    loadResourceStats().catch(() => {})
  }, [])

  const stats = useMemo(() => ({
    total: vms.length,
    running: vms.filter(v=>v.status==='running').length,
    stopped: vms.filter(v=>v.status==='stopped').length,
    templates: templates.length,
  }), [vms, templates])

  return <div>
    <h2>{user.role} Dashboard</h2>

    <div className='card-grid'>
      {Object.entries(stats).map(([k,v])=><div key={k} className='stat-card'><div className='label'>{k.toUpperCase()}</div><div className='value'>{v}</div></div>)}
    </div>

    <section className='panel' style={{marginTop:16}}>
      <div className='group' style={{justifyContent:'space-between'}}>
        <h3>Proxmox Cluster Resources</h3>
        <button onClick={loadResourceStats} disabled={loadingStats}>{loadingStats ? 'Refreshing…' : 'Refresh'}</button>
      </div>

      {statsError ? <p className='muted'>Failed to load Proxmox resource stats: {statsError}</p> : null}
      {!statsError && !resourceStats ? <p className='muted'>Loading live Proxmox resource statistics…</p> : null}

      {resourceStats ? <>
        {resourceStats.config_source === 'env_fallback' ? <p className='muted'>Using .env Proxmox fallback. Configure Admin &gt; Proxmox Setup for database-managed cluster access.</p> : null}
        {resourceStats.config_source === 'not_configured' ? <p className='muted'>Proxmox is not configured. <Link to='/admin/proxmox-setup'>Open Proxmox Setup</Link>.</p> : null}

        <div className='card-grid'>
          <div className='stat-card'><div className='label'>CLUSTER</div><div className='value'>{resourceStats.cluster?.name || 'N/A'}</div></div>
          <div className='stat-card'><div className='label'>CONFIG SOURCE</div><div className='value'>{resourceStats.config_source}</div></div>
          <div className='stat-card'><div className='label'>LAST REFRESH</div><div className='value'>{resourceStats.fetched_at ? new Date(resourceStats.fetched_at).toLocaleString() : '—'}</div></div>
          <div className='stat-card'><div className='label'>NODES</div><div className='value'>{resourceStats.summary?.total_nodes ?? 0} ({resourceStats.summary?.online_nodes ?? 0} online)</div></div>
          <div className='stat-card'><div className='label'>VMS</div><div className='value'>{resourceStats.summary?.total_vms ?? 0} total / {resourceStats.summary?.running_vms ?? 0} running</div></div>
          <div className='stat-card'><div className='label'>TEMPLATES</div><div className='value'>{resourceStats.summary?.templates ?? 0}</div></div>
          <div className='stat-card'><div className='label'>CPU USAGE</div><div className='value'>{formatPct(resourceStats.summary?.cpu_usage_percent)}</div></div>
          <div className='stat-card'><div className='label'>MEMORY USAGE</div><div className='value'>{formatPct(resourceStats.summary?.memory_usage_percent)} ({formatBytes(resourceStats.summary?.memory_used_bytes)} / {formatBytes(resourceStats.summary?.memory_total_bytes)})</div></div>
          <div className='stat-card'><div className='label'>DISK USAGE</div><div className='value'>{formatPct(resourceStats.summary?.disk_usage_percent)} ({formatBytes(resourceStats.summary?.disk_used_bytes)} / {formatBytes(resourceStats.summary?.disk_total_bytes)})</div></div>
        </div>

        {Array.isArray(resourceStats.warnings) && resourceStats.warnings.length ? <ul>{resourceStats.warnings.map((w, i)=><li key={i} className='muted'>{w}</li>)}</ul> : null}

        <h4>Per-node inventory</h4>
        {!Array.isArray(resourceStats.nodes) || resourceStats.nodes.length === 0 ? <p className='muted'>No node data available.</p> : (
          <table className='vm-table'>
            <thead><tr><th>Node</th><th>Status</th><th>CPU</th><th>Memory</th><th>Disk</th><th>VMs</th><th>Running</th><th>Stopped</th><th>Templates</th><th>Uptime</th></tr></thead>
            <tbody>
              {resourceStats.nodes.map((n)=><tr key={n.name}>
                <td>{n.name}</td>
                <td>{n.status}</td>
                <td>{formatPct(n.cpu_usage_percent)} ({n.cpu_count ?? '—'} cores)</td>
                <td>{formatPct(n.memory_usage_percent)} ({formatBytes(n.memory_used_bytes)} / {formatBytes(n.memory_total_bytes)})</td>
                <td>{formatPct(n.disk_usage_percent)} ({formatBytes(n.disk_used_bytes)} / {formatBytes(n.disk_total_bytes)})</td>
                <td>{n.vm_count ?? 0}</td>
                <td>{n.running_vm_count ?? 0}</td>
                <td>{n.stopped_vm_count ?? 0}</td>
                <td>{n.template_count ?? 0}</td>
                <td>{formatUptime(n.uptime_seconds)}</td>
              </tr>)}
            </tbody>
          </table>
        )}
      </> : null}
    </section>
  </div>
}
