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

  return <section className='page-shell' aria-labelledby='events-title'>
    <header className='ui-page-header'><div><p className='muted'>Teaching</p><h2 id='events-title'>Events and tasks</h2><p className='ui-page-header__description'>Search recent classroom operations, warnings, and outcomes.</p></div></header>
    <section className='panel' aria-labelledby='event-results-title'>
    <form className='ui-form-grid' onSubmit={event=>{event.preventDefault();load()}} aria-label='Event filters'>
      <label className='ui-field'>Search<input className='input' type='search' value={q} onChange={e=>setQ(e.target.value)} /></label>
      <label className='ui-field'>Severity<select className='input' value={severity} onChange={e=>setSeverity(e.target.value)}>
        <option value=''>All severity</option>
        <option value='info'>Info</option>
        <option value='warning'>Warning</option>
        <option value='error'>Error</option>
        <option value='task'>Task</option>
      </select></label>
      <div className='ui-cluster ui-form-grid__wide'><button type='submit' disabled={loading}>{loading ? 'Loading…' : 'Apply filters'}</button></div>
    </form>
    <h3 id='event-results-title'>Results</h3>
    {error ? <p className='msg error' role='alert'>{error}</p> : null}
    {loading ? <p className='muted' role='status'>Loading events…</p> : null}
    {!loading && !error && !items.length ? <p className='muted'>No events match the current filters.</p> : null}
    {items.length ? <div className='ui-table-wrap' role='region' aria-labelledby='event-results-title' tabIndex='0'><table className='ui-table'><thead><tr><th scope='col'>Time</th><th scope='col'>Type</th><th scope='col'>Severity</th><th scope='col'>Task or event</th><th scope='col'>Status</th><th scope='col'>Source</th></tr></thead><tbody>
      {items.map(i => <tr key={i.id}><td>{i.time}</td><td>{i.type}</td><td>{i.severity}</td><td>{i.message}</td><td>{i.status || '-'}</td><td>{i.source}</td></tr>)}
    </tbody></table></div> : null}
    </section>
  </section>
}
