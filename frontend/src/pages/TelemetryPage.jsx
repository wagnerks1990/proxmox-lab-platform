import { useEffect, useState } from 'react'
import { getTelemetrySummary, getTelemetryEvents } from '../services/telemetryApi'
import { getAnalyticsSummary } from '../services/analyticsApi'
import StatCard from '../components/operational/StatCard'
import RecentEventsTable from '../components/operational/RecentEventsTable'
import LiveEventStreamPanel from '../components/operational/LiveEventStreamPanel'
import useOperationalEvents from '../hooks/useOperationalEvents'
import { useOperationalStore } from '../state/operationalStore'

export default function TelemetryPage(){
 const [summary,setSummary]=useState({}); const [events,setEvents]=useState([]); const [analytics,setAnalytics]=useState({}); const live=useOperationalStore(); useOperationalEvents()
 useEffect(()=>{getTelemetrySummary().then(setSummary).catch(()=>setSummary({})); getTelemetryEvents().then((rows)=>setEvents(Array.isArray(rows)?rows:[])).catch(()=>setEvents([])); getAnalyticsSummary().then(setAnalytics).catch(()=>setAnalytics({}))},[])
 return <section><h2>Telemetry</h2><p className='muted'>Recent telemetry events and live stream status.</p><div className='group'><StatCard label='Active Sessions' value={summary.in_memory?.active_session_count}/><StatCard label='Reconnect Attempts' value={summary.in_memory?.reconnect_attempts}/><StatCard label='Failures' value={summary.failures}/><StatCard label='Active Sessions (Analytics)' value={analytics.active_sessions}/></div><div className='muted'>Live: {live.status}</div>{events.length===0?<p className='muted'>No telemetry events yet.</p>:null}<RecentEventsTable rows={events}/><LiveEventStreamPanel/></section>
}
