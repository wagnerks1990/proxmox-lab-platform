import { useCallback, useEffect, useState } from 'react'
import LiveEventStreamPanel from '../components/operational/LiveEventStreamPanel'
import RecentEventsTable from '../components/operational/RecentEventsTable'
import { EmptyState, ErrorState, LoadingState } from '../components/workflows/WorkflowState'
import WorkflowStatus from '../components/workflows/WorkflowStatus'
import useOperationalEvents from '../hooks/useOperationalEvents'
import { getAnalyticsSummary } from '../services/analyticsApi'
import { getTelemetryEvents, getTelemetrySummary } from '../services/telemetryApi'
import { useOperationalStore } from '../state/operationalStore'

const errorDetail = error => {
  const value = error?.response?.data?.detail
  return typeof value === 'string' ? value : 'Telemetry could not be loaded.'
}

export default function TelemetryPage() {
  const [summary, setSummary] = useState({})
  const [events, setEvents] = useState([])
  const [analytics, setAnalytics] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const live = useOperationalStore()
  useOperationalEvents()

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [summaryResult, eventResult, analyticsResult] = await Promise.all([
        getTelemetrySummary(), getTelemetryEvents(), getAnalyticsSummary(),
      ])
      setSummary(summaryResult || {})
      setEvents(Array.isArray(eventResult) ? eventResult : [])
      setAnalytics(analyticsResult || {})
    } catch (requestError) {
      setError(errorDetail(requestError))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) return <LoadingState label='Loading telemetry…' />
  if (error) return <ErrorState message={error} onRetry={load} retrying={loading} />

  return <section className='page-shell' aria-labelledby='telemetry-title'>
    <header className='ui-page-header'>
      <div className='ui-page-header__copy'><p className='muted'>Platform observability</p><h1 id='telemetry-title' className='ui-page-header__title'>Telemetry</h1><p className='ui-page-header__description'>Session health, failures, and recent application signals.</p></div>
      <div className='ui-page-header__actions'><button type='button' onClick={load}>Refresh</button></div>
    </header>
    <div className='card-grid' aria-label='Telemetry summary'>
      <div className='stat-card'><div className='label'>ACTIVE SESSIONS</div><div className='value'>{summary.in_memory?.active_session_count ?? 0}</div></div>
      <div className='stat-card'><div className='label'>RECONNECT ATTEMPTS</div><div className='value'>{summary.in_memory?.reconnect_attempts ?? 0}</div></div>
      <div className='stat-card'><div className='label'>FAILURES</div><div className='value'>{summary.failures ?? 0}</div></div>
      <div className='stat-card'><div className='label'>ANALYTICS SESSIONS</div><div className='value'>{analytics.active_sessions ?? 0}</div></div>
    </div>
    <section className='panel' aria-labelledby='telemetry-events-title'>
      <div className='panel-head'><div><h2 id='telemetry-events-title'>Recent events</h2><p className='muted'>Newest platform telemetry reported by the server.</p></div><WorkflowStatus value={live.connected ? 'running' : live.status} /></div>
      {!events.length ? <EmptyState title='No telemetry events' message='The platform has not recorded any telemetry events yet.' /> : <div className='ui-table-wrap' role='region' aria-labelledby='telemetry-events-title' tabIndex='0'><RecentEventsTable rows={events} /></div>}
    </section>
    <details className='panel'>
      <summary>Live stream diagnostics</summary>
      <p className='muted'>Connection timing and raw transition data for advanced troubleshooting.</p>
      <LiveEventStreamPanel />
    </details>
  </section>
}
