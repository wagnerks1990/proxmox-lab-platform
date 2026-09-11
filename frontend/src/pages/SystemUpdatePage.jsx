import { useEffect, useState } from 'react'
import { applyUpdate, checkForUpdate, getUpdateStatus, rollbackUpdate, saveUpdateSettings } from '../services/updateApi'

const operationTone = status => ['succeeded','success','idle'].includes(String(status).toLowerCase()) ? 'ui-status-badge--success' : ['failed','error'].includes(String(status).toLowerCase()) ? 'ui-status-badge--danger' : 'ui-status-badge--warning'

export default function SystemUpdatePage({ setMessage }) {
  const [data,setData]=useState(null); const [busy,setBusy]=useState(false); const [form,setForm]=useState(null); const [loadError,setLoadError]=useState('')
  const load=async()=>{setLoadError('');try{const current=await getUpdateStatus();setData(current);setForm(current.settings)}catch(error){const text=error?.response?.data?.detail||error.message||'Unable to load update status.';setLoadError(text);setMessage({ type: 'error', text });throw error}}
  useEffect(()=>{load().catch(()=>{})},[])
  useEffect(()=>{const state=String(data?.agent?.operation?.status||data?.latest_run?.status||'').toLowerCase();if(!['queued','running'].includes(state))return;const timer=setInterval(()=>load().catch(()=>{}),2000);return()=>clearInterval(timer)},[data?.agent?.operation?.status,data?.latest_run?.status])
  const perform=async(label,action)=>{if(!window.confirm(`${label}? The service may be temporarily unavailable.`))return;setBusy(true);try{const result=await action();setMessage({ type: 'success', text: result.message||`${label} requested` });await load()}catch(error){setMessage({ type: 'error', text: error?.response?.data?.detail||error.message })}finally{setBusy(false)}}
  const save=async event=>{event.preventDefault();setBusy(true);try{await saveUpdateSettings(form);setMessage({ type: 'success', text: 'Update settings saved' });await load()}catch(error){setMessage({ type: 'error', text: error?.response?.data?.detail||error.message })}finally{setBusy(false)}}

  if(!data||!form)return <section className='page-shell' aria-labelledby='updates-title'><header className='ui-page-header'><div><h2 id='updates-title'>System updates</h2><p className='ui-page-header__description'>Health-gated application and database updates.</p></div></header>{loadError?<div className='ui-alert ui-alert--error' role='alert'><span>{loadError}</span><button onClick={()=>load().catch(()=>{})}>Try again</button></div>:<p className='muted' role='status'>Loading update controller…</p>}</section>
  const operationStatus=data.agent?.operation?.status||data.latest_run?.status
  return <section className='page-shell' aria-labelledby='updates-title'>
    <header className='ui-page-header'><div className='ui-page-header__copy'><p className='muted'>Administration</p><h2 id='updates-title' className='ui-page-header__title'>System updates</h2><p className='ui-page-header__description'>Health-gated GitHub updates with a database backup and rollback point.</p></div></header>
    {loadError?<p className='ui-alert ui-alert--error' role='alert'>{loadError}</p>:null}
    <section className='ui-card' aria-labelledby='deployment-title'><div className='ui-card__header'><div><h3 id='deployment-title'>Deployment</h3><p className='ui-card__description'>Review the exact versions before starting a host operation.</p></div>{operationStatus?<span className={`ui-status-badge ${operationTone(operationStatus)}`}>{operationStatus}</span>:null}</div>
      <dl className='detail-list'><div><dt>Repository</dt><dd>{data.repository}</dd></div><div><dt>Current version</dt><dd>{data.agent?.current_version||'Updater unavailable'}</dd></div><div><dt>Rollback version</dt><dd>{data.agent?.previous_version||'No rollback point'}</dd></div></dl>
      {!data.agent?.available?<p className='ui-alert ui-alert--error' role='alert'>Host update agent unavailable: {data.agent?.message}</p>:null}
      <div className='ui-cluster'><button disabled={busy||!data.agent?.available} onClick={()=>perform('Check for updates',checkForUpdate)}>Check for updates</button><button disabled={busy||!data.agent?.available||!data.latest_run?.to_version} onClick={()=>perform('Apply checked commit',()=>applyUpdate(data.latest_run.to_version))}>Apply checked commit</button><button className='ui-button--danger' disabled={busy||!data.agent?.previous_version} onClick={()=>perform('Roll back application and database',rollbackUpdate)}>Rollback</button></div>
    </section>
    <details className='ui-card' open><summary><strong>Automatic update settings</strong></summary><form className='ui-form-grid' onSubmit={save}>
      <label className='ui-field ui-form-grid__wide'><input type='checkbox' checked={form.automatic_updates} onChange={event=>setForm({...form,automatic_updates:event.target.checked})}/> Enable automatic updates</label>
      <label className='ui-field'>Branch<input className='input' value={form.branch} onChange={event=>setForm({...form,branch:event.target.value})}/></label>
      <label className='ui-field'>Channel<select className='input' value={form.channel} onChange={event=>setForm({...form,channel:event.target.value})}><option value='stable'>Stable</option><option value='candidate'>Candidate</option><option value='development'>Development</option></select></label>
      <label className='ui-field'>Check interval (minutes)<input className='input' type='number' min='15' max='10080' value={form.check_interval_minutes} onChange={event=>setForm({...form,check_interval_minutes:Number(event.target.value)})}/></label>
      <label className='ui-field'>Maintenance hour (UTC)<input className='input' type='number' min='0' max='23' value={form.maintenance_hour_utc} onChange={event=>setForm({...form,maintenance_hour_utc:Number(event.target.value)})}/></label>
      <div className='ui-cluster ui-form-grid__wide'><button type='submit' disabled={busy}>Save settings</button></div>
    </form></details>
    {data.latest_run?<details className='ui-card'><summary><strong>Latest operation</strong> · {data.latest_run.action}</summary><p><span className={`ui-status-badge ${operationTone(data.latest_run.status)}`}>{data.latest_run.status}</span></p><p className='muted'>{data.latest_run.details}</p></details>:null}
  </section>
}
