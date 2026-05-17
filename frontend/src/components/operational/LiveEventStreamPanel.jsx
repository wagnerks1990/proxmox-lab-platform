import useEventStream from '../../hooks/useEventStream'

export default function LiveEventStreamPanel(){
  const { status, events, tokenExpiry } = useEventStream('/api/admin/events/stream')
  const expiryText = tokenExpiry ? new Date(tokenExpiry * 1000).toISOString() : 'unknown'
  return <div className='panel'><h4>Live stream ({status})</h4><div className='muted'>Token exp: {expiryText}</div><pre>{events.join('\n')}</pre></div>
}
