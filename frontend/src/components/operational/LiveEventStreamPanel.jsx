import { useOperationalStore } from '../../state/operationalStore'

export default function LiveEventStreamPanel(){
  const live = useOperationalStore()
  const expiryText = live.tokenExpiry ? new Date(live.tokenExpiry * 1000).toISOString() : 'unknown'
  const d = live.debug || {}
  return <div className='panel'>
    <h4>Live stream ({live.status})</h4>
    <div className='muted'>connected: {String(live.connected)} | error: {String(live.error)}</div>
    <div className='muted'>Token exp: {expiryText}</div>
    <div className='muted'>onopen: {d.lastOnOpenAt || 'n/a'} | onmessage: {d.lastOnMessageAt || 'n/a'} | heartbeat: {d.lastHeartbeatAt || 'n/a'}</div>
    <div className='muted'>reconnects: {d.reconnectCount ?? 0} | readyState: {String(d.readyState)}</div>
    <details><summary>Transitions</summary><pre>{JSON.stringify(d.transitions || [], null, 2)}</pre></details>
    <pre>{(live.events||[]).join('\n')}</pre>
  </div>
}
