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
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState(null)
  const [events, setEvents] = useState([])
  const [tokenExpiry, setTokenExpiry] = useState(null)
  const retryRef = useRef(null)

  useEffect(() => {
    let es = null
    let stopped = false

    const clearRetry = () => {
      if (retryRef.current) clearTimeout(retryRef.current)
      retryRef.current = null
    }

    const scheduleReconnect = (ms = 3000) => {
      if (stopped) return
      clearRetry()
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

      const { token, state } = tokenState()
      if (state !== 'ok') {
        setStatus(state)
        setConnected(false)
        setError(state)
        scheduleReconnect(5000)
        return
      }

      setStatus('connecting')
      setConnected(false)
      setError(null)

      es = new EventSource(buildUrl(token))

      es.onopen = () => {
        setStatus('connected')
        setConnected(true)
        setError(null)
      }

      es.onmessage = (e) => {
        setEvents((prev) => [e.data, ...prev].slice(0, 30))
        if (!connected) {
          setStatus('connected')
          setConnected(true)
          setError(null)
        }
      }

      es.onerror = () => {
        es?.close()
        const nowState = tokenState().state
        setConnected(false)
        if (nowState === 'ok') {
          setStatus('error')
          setError('stream_error')
          scheduleReconnect(3000)
        } else {
          setStatus(nowState)
          setError(nowState)
          scheduleReconnect(5000)
        }
      }
    }

    const onStorage = (evt) => {
      if (evt.key === 'token') connect()
    }
    window.addEventListener('storage', onStorage)

    connect()

    return () => {
      stopped = true
      clearRetry()
      es?.close()
      window.removeEventListener('storage', onStorage)
    }
  }, [url])

  return { status, connected, error, events, tokenExpiry }
}
