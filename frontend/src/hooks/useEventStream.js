import { useEffect, useRef, useState } from 'react'

function parseJwtExp(token) {
  try {
    const payload = JSON.parse(atob((token || '').split('.')[1] || ''))
    return typeof payload.exp === 'number' ? payload.exp : null
  } catch {
    return null
  }
}

export default function useEventStream(url = '/api/admin/events/stream') {
  const [status, setStatus] = useState('connecting')
  const [events, setEvents] = useState([])
  const [tokenExpiry, setTokenExpiry] = useState(null)
  const retryRef = useRef(null)
  const lastTokenRef = useRef(null)

  useEffect(() => {
    let es = null
    let stopped = false

    const clearRetry = () => {
      if (retryRef.current) {
        clearTimeout(retryRef.current)
        retryRef.current = null
      }
    }

    const scheduleReconnect = (ms = 3000) => {
      clearRetry()
      retryRef.current = setTimeout(() => {
        if (!stopped) connect()
      }, ms)
    }

    const isTokenExpired = (token) => {
      const exp = parseJwtExp(token)
      setTokenExpiry(exp)
      if (!exp) return false
      const now = Math.floor(Date.now() / 1000)
      return exp <= now
    }

    const buildSseUrl = (token) => `${url}${url.includes('?') ? '&' : '?'}token=${encodeURIComponent(token || '')}`

    const probeAuth = async (token) => {
      const probe = await fetch(buildSseUrl(token), { method: 'GET', headers: { Accept: 'text/event-stream' } })
      return probe.status
    }

    const connect = async () => {
      const token = localStorage.getItem('token') || ''

      if (!token) {
        setStatus('auth_missing')
        scheduleReconnect(5000)
        return
      }

      if (isTokenExpired(token)) {
        setStatus('auth_expired')
        scheduleReconnect(5000)
        return
      }

      try {
        const statusCode = await probeAuth(token)
        if (statusCode === 401) {
          setStatus('auth_expired')
          scheduleReconnect(5000)
          return
        }
      } catch {
        setStatus('disconnected')
        scheduleReconnect(3000)
        return
      }

      lastTokenRef.current = token
      es = new EventSource(buildSseUrl(token))
      es.onopen = () => setStatus('live')
      es.onmessage = (e) => setEvents((p) => [e.data, ...p].slice(0, 30))
      es.onerror = () => {
        es?.close()
        const currentToken = localStorage.getItem('token') || ''
        if (!currentToken || currentToken !== lastTokenRef.current || isTokenExpired(currentToken)) {
          setStatus(currentToken ? 'auth_expired' : 'auth_missing')
          scheduleReconnect(5000)
          return
        }
        setStatus('disconnected')
        scheduleReconnect(3000)
      }
    }

    connect()

    return () => {
      stopped = true
      clearRetry()
      es?.close()
    }
  }, [url])

  return { status, events, tokenExpiry }
}
