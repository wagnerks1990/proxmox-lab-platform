export default function HealthPanel({ health }) {
  const ok = x => x?.ok === true
  return <div className='panel'>
    <h4>System Health</h4>
    <div className='health-grid'>
      <div>Backend <strong>{health?.backend || 'unknown'}</strong></div>
      <div>Database <strong>{ok(health?.database) ? 'ok' : 'issue'}</strong></div>
      <div>Proxmox <strong>{ok(health?.proxmox) ? 'ok' : 'issue'}</strong></div>
    </div>
  </div>
}
