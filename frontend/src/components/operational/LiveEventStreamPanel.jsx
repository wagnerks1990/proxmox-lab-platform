import { useOperationalStore } from '../../state/operationalStore'

export default function LiveEventStreamPanel(){
  const live = useOperationalStore()
  const expiryText = live.tokenExpiry ? new Date(live.tokenExpiry * 1000).toISOString() : 'unknown'
  return <div className='panel'><h4>Live stream ({live.status})</h4><div className='muted'>Token exp: {expiryText}</div><pre>{(live.events||[]).join('\n')}</pre></div>
}
