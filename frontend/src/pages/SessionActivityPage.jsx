import { useEffect, useState } from 'react'
import api from '../services/api'

export default function SessionActivityPage({ setMessage }) {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true); setError('')
    try { const response = await api.get('/admin/session-activity'); setRows(Array.isArray(response.data) ? response.data : []) }
    catch { setRows([]); setError('Unable to load session activity.'); setMessage({ type: 'error', text: 'Unable to load session activity.' }) }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  return <section className='page-shell' aria-labelledby='sessions-title'>
    <header className='ui-page-header'><div><p className='muted'>Teaching</p><h2 id='sessions-title'>Session activity</h2><p className='ui-page-header__description'>Recent console and protocol launches for the selected organization.</p></div><button onClick={load} disabled={loading}>{loading?'Refreshing…':'Refresh'}</button></header>
    {error?<p className='msg error' role='alert'>{error}</p>:null}
    {!loading&&!error&&rows.length===0?<p className='muted'>No session activity records yet.</p>:null}
    {rows.length?<div className='ui-table-wrap' role='region' aria-labelledby='sessions-title' tabIndex='0'><table className='ui-table'>
      <thead><tr><th scope='col'>Time</th><th scope='col'>Actor</th><th scope='col'>VM</th><th scope='col'>Protocol</th><th scope='col'>Status</th><th scope='col'>Details</th></tr></thead>
      <tbody>
        {rows.map(x => <tr key={x.id}><td>{x.created_at || '-'}</td><td>{x.actor_id}</td><td>{x.vm_id}</td><td>{x.protocol}</td><td>{x.status}</td><td>{x.details || '-'}</td></tr>)}
      </tbody>
    </table></div>:null}
  </section>
}
