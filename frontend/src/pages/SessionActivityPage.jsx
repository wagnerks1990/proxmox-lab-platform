import { useEffect, useState } from 'react'
import api from '../services/api'

export default function SessionActivityPage({ setMessage }) {
  const [rows, setRows] = useState([])
  const [filters, setFilters] = useState({ protocol: '', status: '', username: '' })

  const load = () => {
    api.get('/admin/session-activity', { params: filters }).then(r => setRows(r.data)).catch(() => {
      setMessage({ type: 'error', text: 'Unable to load session activity.' })
    })
  }

  useEffect(() => { load() }, [])

  return <section className='panel'>
    <div className='panel-head'>
      <div>
        <h3>Session Activity</h3>
        <p className='muted'>Recent protocol launches and outcomes.</p>
      </div>
      <button onClick={load}>Refresh</button>
    </div>

    <div className='group' style={{ marginBottom: 12 }}>
      <input className='input' placeholder='Filter user' value={filters.username} onChange={e => setFilters({ ...filters, username: e.target.value })} />
      <input className='input' placeholder='Protocol (WEB_TERMINAL/NOVNC/...)' value={filters.protocol} onChange={e => setFilters({ ...filters, protocol: e.target.value })} />
      <input className='input' placeholder='Status (success/failed/pending)' value={filters.status} onChange={e => setFilters({ ...filters, status: e.target.value })} />
      <button onClick={load}>Apply</button>
    </div>

    <table className='vm-table'>
      <thead><tr><th>User</th><th>VM Name</th><th>Protocol</th><th>Launch Time</th><th>Status</th><th>Details</th></tr></thead>
      <tbody>
        {rows.map(x => {
          const parts = (x.details || '').split(';')
          const userPart = parts.find(p => p.trim().startsWith('user=')) || 'user=-'
          const vmPart = parts.find(p => p.trim().startsWith('vm=')) || 'vm=-'
          return <tr key={x.id}><td>{userPart.replace('user=', '').trim()}</td><td>{vmPart.replace('vm=', '').trim()}</td><td>{x.protocol}</td><td>{x.created_at || '-'}</td><td>{x.status}</td><td>{x.details || '-'}</td></tr>
        })}
      </tbody>
    </table>
  </section>
}
