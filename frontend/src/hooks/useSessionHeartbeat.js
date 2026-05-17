import { useEffect, useRef } from 'react'
import api from '../services/api'

export default function useSessionHeartbeat(sessionId, enabled = true, intervalMs = 30000) {
  const timer = useRef(null)
  useEffect(() => {
    if (!sessionId || !enabled) return
    const send = () => api.post(`/sessions/${sessionId}/heartbeat`, {})
    send()
    timer.current = setInterval(send, intervalMs)
    return () => timer.current && clearInterval(timer.current)
  }, [sessionId, enabled, intervalMs])
}
