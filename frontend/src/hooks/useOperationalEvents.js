import { useEffect } from 'react'
import useEventStream from './useEventStream'
import { appendOperationalEvent, updateOperational } from '../state/operationalStore'

export default function useOperationalEvents(){
  const { status, events } = useEventStream('/api/admin/events/stream')
  useEffect(()=>{ updateOperational({ status }) }, [status])
  useEffect(()=>{ if(events[0]) appendOperationalEvent(events[0]) }, [events])
}
