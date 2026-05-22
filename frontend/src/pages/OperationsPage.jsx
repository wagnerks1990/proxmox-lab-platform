import { useEffect, useState } from 'react'
import { getOperationsHealth } from '../services/operationsApi'
import { getWorkerRuns } from '../services/workersApi'
import { useOperationalStore } from '../state/operationalStore'
import useOperationalEvents from '../hooks/useOperationalEvents'
import HealthBadge from '../components/operational/HealthBadge'
import { getReconciliationSummary } from '../services/reconciliationApi'
import StatCard from '../components/operational/StatCard'

export default function OperationsPage(){
  const [h,setH]=useState({})
  const [runs,setRuns]=useState([])
  const [rec,setRec]=useState({})
  const live=useOperationalStore()
  useOperationalEvents()

  useEffect(()=>{
    getOperationsHealth().then(setH).catch(()=>setH({}))
    getWorkerRuns().then((rows)=>setRuns(Array.isArray(rows)?rows:[])).catch(()=>setRuns([]))
    getReconciliationSummary().then(setRec).catch(()=>setRec({}))
  },[])

  return <section><h2>Operations</h2><div>Live stream: <HealthBadge value={live.connected?'ok':'error'}/> ({live.status})</div><div className='group'><StatCard label='Pools' value={rec.pools_total}/><StatCard label='Stale Sessions' value={rec.stale_sessions}/><StatCard label='Reconciliation Warnings' value={rec.warnings}/></div><div>Database: <HealthBadge value={h.database||h.db_status}/></div><div>Scheduler Running: {String(Boolean(h.scheduler_running))}</div>{runs.length===0?<p className='muted'>No worker runs recorded yet.</p>:null}<table className='vm-table'><thead><tr><th>Worker</th><th>Status</th><th>Started</th></tr></thead><tbody>{runs.map(r=><tr key={r.id}><td>{r.worker_name}</td><td>{r.status}</td><td>{r.started_at}</td></tr>)}</tbody></table></section>
}
