import { useEffect, useState } from 'react'
import api from '../services/api'
import HealthBadge from '../components/operational/HealthBadge'
export default function OperationsPage(){const [h,setH]=useState({}); const [runs,setRuns]=useState([]); useEffect(()=>{api.get('/admin/operations/health').then(r=>setH(r.data.data||{})); api.get('/admin/workers/runs').then(r=>setRuns(r.data.data||[]))},[]); return <section><h2>Operations</h2><div>Database: <HealthBadge value={h.database}/></div><div>Scheduler Running: {String(h.scheduler_running)}</div><table className='vm-table'><thead><tr><th>Worker</th><th>Status</th><th>Started</th></tr></thead><tbody>{runs.map(r=><tr key={r.id}><td>{r.worker_name}</td><td>{r.status}</td><td>{r.started_at}</td></tr>)}</tbody></table></section>}
