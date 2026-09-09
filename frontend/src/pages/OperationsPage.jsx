import { useEffect, useState } from 'react'
import { listOperations } from '../services/operationsApi'

const activeStates = new Set(['queued', 'running'])

export default function OperationsPage() {
  const [operations, setOperations] = useState([])
  const load = () => listOperations().then(setOperations).catch(() => setOperations([]))

  useEffect(() => { load() }, [])
  useEffect(() => {
    if (!operations.some(operation => activeStates.has(String(operation.state).toLowerCase()))) return
    const timer = setInterval(load, 2000)
    return () => clearInterval(timer)
  }, [operations])

  return <section><h2>Operations</h2><p className='muted'>Durable VM operation progress and history for the selected classroom organization.</p>{operations.length === 0 ? <p className='muted'>No durable operations recorded yet.</p> : null}<table className='vm-table'><thead><tr><th>ID</th><th>Operation</th><th>Target</th><th>State</th><th>Attempts</th><th>Error</th></tr></thead><tbody>{operations.map(row => <tr key={row.id}><td>{row.id}</td><td>{row.operation_type}</td><td>{row.target_type}:{row.target_id}</td><td>{row.state}</td><td>{row.attempts}</td><td>{row.error || '-'}</td></tr>)}</tbody></table></section>
}
