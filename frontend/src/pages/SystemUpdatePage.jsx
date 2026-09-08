import { useEffect, useState } from 'react'
import { applyUpdate, checkForUpdate, getUpdateStatus, rollbackUpdate, saveUpdateSettings } from '../services/updateApi'

export default function SystemUpdatePage({ setMessage }) {
  const [data, setData] = useState(null)
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState(null)

  const load = async () => {
    const current = await getUpdateStatus()
    setData(current)
    setForm(current.settings)
  }
  useEffect(() => { load().catch(e => setMessage(e?.response?.data?.detail || e.message)) }, [])

  const perform = async (label, action) => {
    if (!window.confirm(`${label}? The service may be temporarily unavailable.`)) return
    setBusy(true)
    try {
      const result = await action()
      setMessage(result.message || `${label} requested`)
      await load()
    } catch (e) {
      setMessage(e?.response?.data?.detail || e.message)
    } finally { setBusy(false) }
  }

  const save = async () => {
    setBusy(true)
    try { await saveUpdateSettings(form); setMessage('Update settings saved'); await load() }
    catch (e) { setMessage(e?.response?.data?.detail || e.message) }
    finally { setBusy(false) }
  }

  if (!data || !form) return <div className='panel'>Loading update controller…</div>
  return <div>
    <div className='panel-head'><h2>System Updates</h2><p className='muted'>Health-gated GitHub updates with a database backup and rollback point.</p></div>
    <div className='panel'>
      <h3>Deployment</h3>
      <p><b>Repository:</b> {data.repository}</p>
      <p><b>Current version:</b> {data.agent?.current_version || 'Updater unavailable'}</p>
      <p><b>Previous version:</b> {data.agent?.previous_version || 'No rollback point'}</p>
      {!data.agent?.available && <p className='error'>Host update agent unavailable: {data.agent?.message}</p>}
      {data.agent?.operation && <p><b>Host operation:</b> {data.agent.operation.status}</p>}
      <div className='actions'>
        <button disabled={busy || !data.agent?.available} onClick={() => perform('Check for updates', checkForUpdate)}>Check</button>
        <button disabled={busy || !data.agent?.available || !data.latest_run?.to_version} onClick={() => perform('Apply checked commit', () => applyUpdate(data.latest_run.to_version))}>Update checked commit</button>
        <button disabled={busy || !data.agent?.previous_version} onClick={() => perform('Roll back application and database', rollbackUpdate)}>Rollback</button>
      </div>
    </div>
    <div className='panel'>
      <h3>Automatic updates</h3>
      <label><input type='checkbox' checked={form.automatic_updates} onChange={e => setForm({...form, automatic_updates:e.target.checked})} /> Enable automatic updates</label>
      <label>Branch<input className='input' value={form.branch} onChange={e => setForm({...form, branch:e.target.value})} /></label>
      <label>Channel<select className='input' value={form.channel} onChange={e => setForm({...form, channel:e.target.value})}><option value='stable'>Stable</option><option value='candidate'>Candidate</option><option value='development'>Development</option></select></label>
      <label>Check interval (minutes)<input className='input' type='number' min='15' max='10080' value={form.check_interval_minutes} onChange={e => setForm({...form, check_interval_minutes:Number(e.target.value)})} /></label>
      <label>Maintenance hour (UTC)<input className='input' type='number' min='0' max='23' value={form.maintenance_hour_utc} onChange={e => setForm({...form, maintenance_hour_utc:Number(e.target.value)})} /></label>
      <button disabled={busy} onClick={save}>Save settings</button>
    </div>
    {data.latest_run && <div className='panel'><h3>Latest operation</h3><p>{data.latest_run.action}: {data.latest_run.status}</p><p className='muted'>{data.latest_run.details}</p></div>}
  </div>
}
