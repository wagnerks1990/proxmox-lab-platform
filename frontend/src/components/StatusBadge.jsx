export default function StatusBadge({ status }) {
  const s = (status || 'unknown').toLowerCase()
  const cls = s === 'running' ? 'running' : s === 'stopped' ? 'stopped' : s === 'provisioning' ? 'provisioning' : 'error'
  return <span className={`status-badge ${cls}`}>{status || 'unknown'}</span>
}
