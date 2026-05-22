import { useEffect, useState } from 'react'
import api from '../services/api'

export default function SessionActivityPage({ setMessage }) {
  const [rows, setRows] = useState([])

  useEffect(() => {
    api.get('/admin/session-activity').then(r => setRows(Array.isArray(r.data) ? r.data : [])).catch(() => {
      setRows([])
      setMessage({ type: 'error', text: 'Unable to load session activity.' })
    })
  }, [setMessage])

  return <section className='panel'>
    <div className='panel-head'>
      <h3>Session Activity</h3>
      <p className='muted'>Recent protocol launches and outcomes.</p>
    </div>
    <table className='vm-table'>
      <thead><tr><th>Time</th><th>Actor</th><th>VM</th><th>Protocol</th><th>Status</th><th>Details</th></tr></thead>
      <tbody>
        {rows.length === 0 ? <tr><td colSpan={6} className='muted'>No session activity yet.</td></tr> : null}
        {rows.map(x => <tr key={x.id}><td>{x.created_at || '-'}</td><td>{x.actor_id}</td><td>{x.vm_id}</td><td>{x.protocol}</td><td>{x.status}</td><td>{x.details || '-'}</td></tr>)}
      </tbody>
    </table>
  </section>
}
