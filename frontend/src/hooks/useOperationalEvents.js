import { useEffect } from 'react'
import useEventStream from './useEventStream'
import { appendOperationalEvent, updateOperational } from '../state/operationalStore'

export default function useOperationalEvents(){
  const { status, connected, error, events } = useEventStream('/api/admin/events/stream')
  useEffect(()=>{ updateOperational({ status, connected, error }) }, [status, connected, error])
  useEffect(()=>{ if(events[0]) appendOperationalEvent(events[0]) }, [events])
}
