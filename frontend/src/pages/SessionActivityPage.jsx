import { useEffect, useState } from 'react'
import api from '../services/api'

export default function SessionActivityPage({ setMessage }) {
  const [rows, setRows] = useState([])
  const [filters, setFilters] = useState({ protocol: '', status: '', username: '' })
  const load = () => api.get('/admin/session-activity', { params: filters }).then(r => setRows(r.data)).catch(() => setMessage({ type: 'error', text: 'Unable to load session activity.' }))
  useEffect(() => { load() }, [])
  return <section className='panel'><div className='panel-head'><h3>Session Activity</h3><button className='btn' onClick={load}>Refresh</button></div><div className='group'><input className='input' placeholder='user' value={filters.username} onChange={e => setFilters({ ...filters, username: e.target.value })} /><input className='input' placeholder='protocol' value={filters.protocol} onChange={e => setFilters({ ...filters, protocol: e.target.value })} /><input className='input' placeholder='status' value={filters.status} onChange={e => setFilters({ ...filters, status: e.target.value })} /><button className='btn ghost' onClick={load}>Apply</button></div><table className='table2'><thead><tr><th>User</th><th>VM Name</th><th>Protocol</th><th>Launch Time</th><th>Status</th><th>Details</th></tr></thead><tbody>{rows.map(x => {const parts = (x.details || '').split(';'); const u = (parts.find(p => p.trim().startsWith('user=')) || 'user=-').replace('user=', '').trim(); const v = (parts.find(p => p.trim().startsWith('vm=')) || 'vm=-').replace('vm=', '').trim(); return <tr key={x.id}><td>{u}</td><td>{v}</td><td>{x.protocol}</td><td>{x.created_at || '-'}</td><td>{x.status}</td><td>{x.details || '-'}</td></tr>})}</tbody></table></section>
}
