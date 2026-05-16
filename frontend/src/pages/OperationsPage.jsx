import { useEffect, useState } from 'react'
import { getOperationsHealth } from '../services/operationsApi'
import { getWorkerRuns } from '../services/workersApi'
import HealthBadge from '../components/operational/HealthBadge'
export default function OperationsPage(){const [h,setH]=useState({}); const [runs,setRuns]=useState([]); useEffect(()=>{getOperationsHealth().then(setH); getWorkerRuns().then(setRuns)},[]); return <section><h2>Operations</h2><div>Database: <HealthBadge value={h.database}/></div><div>Scheduler Running: {String(h.scheduler_running)}</div><table className='vm-table'><thead><tr><th>Worker</th><th>Status</th><th>Started</th></tr></thead><tbody>{runs.map(r=><tr key={r.id}><td>{r.worker_name}</td><td>{r.status}</td><td>{r.started_at}</td></tr>)}</tbody></table></section>}
