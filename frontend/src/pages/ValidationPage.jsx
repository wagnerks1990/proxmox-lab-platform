import { useEffect, useState } from 'react'
import api from '../services/api'

export default function ValidationPage() {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const load = async (run = false) => {
    setLoading(true)
    try { const r = await api.get(run ? '/admin/proxmox/validation/run' : '/admin/proxmox/validation'); setReport(r.data) } finally { setLoading(false) }
  }
  useEffect(() => { load(false) }, [])
  const copy = async () => navigator.clipboard.writeText(JSON.stringify(report, null, 2))
  return <section className='panel'>
    <div className='panel-head'><h2>Cluster Validation</h2><div className='group'><button className='btn' onClick={() => load(true)} disabled={loading}>Re-run</button><button className='btn ghost' onClick={copy} disabled={!report}>Copy report</button></div></div>
    {!report ? <div className='empty-state'>No report yet.</div> : <>
      <div className='cards3'><div className='mini-card'><div className='stat-label'>Errors</div><div className='stat-value'>{report.summary?.errors ?? 0}</div></div><div className='mini-card'><div className='stat-label'>Warnings</div><div className='stat-value'>{report.summary?.warnings ?? 0}</div></div><div className='mini-card'><div className='stat-label'>Passed</div><div className='stat-value'>{report.summary?.passed ?? 0}</div></div></div>
      <table className='table2'><thead><tr><th>Category</th><th>Name</th><th>Status</th><th>Message</th><th>What this means</th></tr></thead><tbody>{(report.checks||[]).map((c,i)=><tr key={i}><td>{c.category}</td><td>{c.name}</td><td>{c.status}</td><td>{c.message}</td><td>{c.fix_hint||'-'}</td></tr>)}</tbody></table>
    </>}
  </section>
}
