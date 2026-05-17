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
  const openTimeoutRef = useRef(null)

  useEffect(() => {
    let es = null
    let stopped = false

    const clearTimers = () => {
      if (retryRef.current) clearTimeout(retryRef.current)
      if (openTimeoutRef.current) clearTimeout(openTimeoutRef.current)
      retryRef.current = null
      openTimeoutRef.current = null
    }

    const scheduleReconnect = (ms = 3000) => {
      if (stopped) return
      if (retryRef.current) clearTimeout(retryRef.current)
      retryRef.current = setTimeout(connect, ms)
    }

    const tokenState = () => {
      const token = localStorage.getItem('token') || ''
      const exp = parseJwtExp(token)
      setTokenExpiry(exp)
      if (!token) return { token, state: 'auth_missing' }
      if (exp && exp <= Math.floor(Date.now() / 1000)) return { token, state: 'auth_expired' }
      return { token, state: 'ok' }
    }

    const buildUrl = (token) => `${url}${url.includes('?') ? '&' : '?'}token=${encodeURIComponent(token || '')}`

    const connect = () => {
      if (stopped) return
      clearTimers()

      const { token, state } = tokenState()
      if (state !== 'ok') {
        setStatus(state)
        scheduleReconnect(5000)
        return
      }

      setStatus('connecting')
      es = new EventSource(buildUrl(token))

      openTimeoutRef.current = setTimeout(() => {
        if (es && es.readyState !== EventSource.OPEN) {
          setStatus('error')
          es.close()
          scheduleReconnect(3000)
        }
      }, 8000)

      es.onopen = () => {
        if (openTimeoutRef.current) clearTimeout(openTimeoutRef.current)
        setStatus('connected')
      }

      es.onmessage = (e) => {
        setEvents((prev) => [e.data, ...prev].slice(0, 30))
      }

      es.onerror = () => {
        es?.close()
        const nowState = tokenState().state
        setStatus(nowState === 'ok' ? 'error' : nowState)
        scheduleReconnect(nowState === 'ok' ? 3000 : 5000)
      }
    }

    const onStorage = (evt) => {
      if (evt.key === 'token') connect()
    }
    window.addEventListener('storage', onStorage)

    connect()

    return () => {
      stopped = true
      clearTimers()
      es?.close()
      window.removeEventListener('storage', onStorage)
    }
  }, [url])

  return { status, events, tokenExpiry }
}
