import { useEffect } from 'react'
import useEventStream from './useEventStream'
import { appendOperationalEvent, pushOperationalTransition, updateOperational, updateOperationalDebug } from '../state/operationalStore'

export default function useOperationalEvents(){
  const stream = useEventStream('/api/admin/events/stream')
  const { status, connected, error, events, tokenExpiry, lastOnOpenAt, lastOnMessageAt, lastHeartbeatAt, reconnectCount, readyState } = stream

  useEffect(()=>{ updateOperational({ status, connected, error, tokenExpiry }) }, [status, connected, error, tokenExpiry])
  useEffect(()=>{ updateOperationalDebug({ lastOnOpenAt, lastOnMessageAt, lastHeartbeatAt, reconnectCount, readyState }) }, [lastOnOpenAt, lastOnMessageAt, lastHeartbeatAt, reconnectCount, readyState])
  useEffect(()=>{ pushOperationalTransition({ at: new Date().toISOString(), status, connected, error, readyState }) }, [status, connected, error, readyState])
  useEffect(()=>{ if(events[0]) appendOperationalEvent(events[0]) }, [events])
}
