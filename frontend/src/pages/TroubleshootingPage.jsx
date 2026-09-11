import { useCallback, useEffect, useState } from 'react'
import { EmptyState, ErrorState, LoadingState } from '../components/workflows/WorkflowState'
import WorkflowStatus from '../components/workflows/WorkflowStatus'
import useOperationalEvents from '../hooks/useOperationalEvents'
import { getTroubleshootingRecent } from '../services/troubleshootingApi'
import { useOperationalStore } from '../state/operationalStore'

const errorDetail = error => {
  const value = error?.response?.data?.detail
  return typeof value === 'string' ? value : 'Troubleshooting information could not be loaded.'
}

export default function TroubleshootingPage() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const live = useOperationalStore()
  useOperationalEvents()

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getTroubleshootingRecent()
      setRows(Array.isArray(data) ? data : [])
    } catch (requestError) {
      setError(errorDetail(requestError))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) return <LoadingState label='Checking platform health…' />
  if (error) return <ErrorState message={error} onRetry={load} retrying={loading} />

  return <section className='page-shell' aria-labelledby='troubleshooting-title'>
    <header className='ui-page-header'>
      <div className='ui-page-header__copy'><p className='muted'>Platform observability</p><h1 id='troubleshooting-title' className='ui-page-header__title'>Troubleshooting</h1><p className='ui-page-header__description'>Current issues and the next useful action for each subsystem.</p></div>
      <div className='ui-page-header__actions'><button type='button' onClick={load}>Run check again</button></div>
    </header>
    <div className='panel-head'><p className='muted'>Live event stream</p><WorkflowStatus value={live.connected ? 'running' : live.status} /></div>
    {!rows.length ? <EmptyState title='No active issues detected' message='LabGoblin did not identify a current platform problem.' /> : <div className='card-grid'>
      {rows.map((issue, index) => <article className={`ui-card ${String(issue.severity).toLowerCase() === 'error' ? 'ui-card--danger' : 'ui-card--warning'}`} key={issue.id || `${issue.issue_type}-${index}`}>
        <div className='ui-card__header'><div><h2 className='ui-card__title'>{issue.title || issue.issue_type || 'Platform issue'}</h2><p className='ui-card__description'>{issue.subsystem || 'Unknown subsystem'}</p></div><WorkflowStatus value={issue.severity || 'warning'} /></div>
        <h3>Recommended action</h3><p>{issue.suggested_fix || 'Review the subsystem logs and retry the failed operation.'}</p>
        <details><summary>Technical details</summary><dl><dt>Category</dt><dd>{issue.category || 'Not reported'}</dd><dt>Probable cause</dt><dd>{issue.probable_cause || 'Not reported'}</dd><dt>Subsystem</dt><dd>{issue.subsystem || 'Not reported'}</dd></dl></details>
      </article>)}
    </div>}
  </section>
}
