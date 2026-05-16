import { useEffect, useState } from 'react'

export default function useEventStream(url = '/api/admin/events/stream') {
  const [status, setStatus] = useState('connecting')
  const [events, setEvents] = useState([])
  useEffect(() => {
    let retry = null
    let es = null
    const connect = () => {
      es = new EventSource(url)
      es.onopen = () => setStatus('live')
      es.onmessage = (e) => setEvents((p) => [e.data, ...p].slice(0, 30))
      es.onerror = () => { setStatus('disconnected'); es.close(); retry = setTimeout(connect, 3000) }
    }
    connect()
    return () => { if (retry) clearTimeout(retry); if (es) es.close() }
  }, [url])
  return { status, events }
}
