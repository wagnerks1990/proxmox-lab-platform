import { useEffect, useState } from 'react'
import { getEvents } from '../services/eventsApi'

export default function EventsPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')
  const [severity, setSeverity] = useState('')

  const load = async () => {
    setLoading(true); setError('')
    try {
      const data = await getEvents({ q, severity, limit: 100, offset: 0 })
      setItems(Array.isArray(data.items) ? data.items : [])
    } catch (e) {
      setError(JSON.stringify(e?.response?.data?.detail || e.message))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return <section className='panel'>
    <h3>Events / Tasks</h3>
    <div className='group'>
      <input className='input' placeholder='Search' value={q} onChange={e=>setQ(e.target.value)} />
      <select className='input' value={severity} onChange={e=>setSeverity(e.target.value)}>
        <option value=''>All severity</option>
        <option value='info'>Info</option>
        <option value='warning'>Warning</option>
        <option value='error'>Error</option>
        <option value='task'>Task</option>
      </select>
      <button onClick={load} disabled={loading}>{loading ? 'Loading…' : 'Refresh'}</button>
    </div>
    {error ? <p className='muted'>{error}</p> : null}
    {loading ? <p className='muted'>Loading events…</p> : null}
    {!loading && !items.length ? <p className='muted'>No events found.</p> : null}
    {items.length ? <table className='vm-table'><thead><tr><th>Time</th><th>Type</th><th>Severity</th><th>Task/Event</th><th>Status</th><th>Source</th></tr></thead><tbody>
      {items.map(i => <tr key={i.id}><td>{i.time}</td><td>{i.type}</td><td>{i.severity}</td><td>{i.message}</td><td>{i.status || '-'}</td><td>{i.source}</td></tr>)}
    </tbody></table> : null}
  </section>
}
