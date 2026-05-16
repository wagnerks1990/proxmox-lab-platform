import { useEffect, useState } from 'react'
import { getTelemetrySummary, getTelemetryEvents } from '../services/telemetryApi'
import StatCard from '../components/operational/StatCard'
import RecentEventsTable from '../components/operational/RecentEventsTable'
import LiveEventStreamPanel from '../components/operational/LiveEventStreamPanel'
import useOperationalEvents from '../hooks/useOperationalEvents'
import { useOperationalStore } from '../state/operationalStore'

export default function TelemetryPage(){
 const [summary,setSummary]=useState({}); const [events,setEvents]=useState([]); const live=useOperationalStore(); useOperationalEvents()
 useEffect(()=>{getTelemetrySummary().then(setSummary); getTelemetryEvents().then(setEvents)},[])
 return <section><h2>Telemetry</h2><div className='group'><StatCard label='Active Sessions' value={summary.in_memory?.active_session_count}/><StatCard label='Reconnect Attempts' value={summary.in_memory?.reconnect_attempts}/><StatCard label='Failures' value={summary.failures}/></div><div className='muted'>Live: {live.status}</div><RecentEventsTable rows={events}/><LiveEventStreamPanel/></section>
}
