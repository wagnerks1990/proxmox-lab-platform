import { useEffect, useState } from 'react'
import { getOperationsHealth } from '../services/operationsApi'
import { getWorkerRuns } from '../services/workersApi'
import { useOperationalStore } from '../state/operationalStore'
import useOperationalEvents from '../hooks/useOperationalEvents'
import HealthBadge from '../components/operational/HealthBadge'
import { getReconciliationSummary } from '../services/reconciliationApi'
import StatCard from '../components/operational/StatCard'
export default function OperationsPage(){const [h,setH]=useState({}); const [runs,setRuns]=useState([]); const [rec,setRec]=useState({}); const live=useOperationalStore(); useOperationalEvents(); useEffect(()=>{getOperationsHealth().then(setH); getWorkerRuns().then(setRuns); getReconciliationSummary().then(setRec)},[]); return <section><h2>Operations</h2><div>Live stream: <HealthBadge value={live.status==='live'?'ok':'error'}/></div><div className='group'><StatCard label='Pools' value={rec.pools_total}/><StatCard label='Stale Sessions' value={rec.stale_sessions}/><StatCard label='Reconciliation Warnings' value={rec.warnings}/></div><div>Database: <HealthBadge value={h.database||h.db_status}/></div><div>Scheduler Running: {String(h.scheduler_running)}</div><table className='vm-table'><thead><tr><th>Worker</th><th>Status</th><th>Started</th></tr></thead><tbody>{runs.map(r=><tr key={r.id}><td>{r.worker_name}</td><td>{r.status}</td><td>{r.started_at}</td></tr>)}</tbody></table></section>}
