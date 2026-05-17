import { useEffect, useRef, useState } from 'react'

function parseJwtExp(token) {
  try {
    const payload = JSON.parse(atob((token || '').split('.')[1] || ''))
    return typeof payload.exp === 'number' ? payload.exp : null
  } catch {
    return null
  }
}

const DEBUG = typeof window !== 'undefined' && window.localStorage?.getItem('debug_sse') === '1'
const dlog = (...args) => { if (DEBUG) console.debug('[SSE]', ...args) }

export default function useEventStream(url = '/api/admin/events/stream') {
  const [status, setStatus] = useState('connecting')
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState(null)
  const [events, setEvents] = useState([])
  const [tokenExpiry, setTokenExpiry] = useState(null)
  const [lastOnOpenAt, setLastOnOpenAt] = useState(null)
  const [lastOnMessageAt, setLastOnMessageAt] = useState(null)
  const [lastHeartbeatAt, setLastHeartbeatAt] = useState(null)
  const [reconnectCount, setReconnectCount] = useState(0)
  const [readyState, setReadyState] = useState(null)
  const retryRef = useRef(null)
  const esRef = useRef(null)

  useEffect(() => {
    let stopped = false

    const transition = (next, meta = {}) => dlog('transition', { from: status, to: next, ...meta })

    const clearRetry = () => {
      if (retryRef.current) clearTimeout(retryRef.current)
      retryRef.current = null
    }

    const scheduleReconnect = (ms = 3000) => {
      if (stopped) return
      setReconnectCount((n) => n + 1)
      clearRetry()
      retryRef.current = setTimeout(connect, ms)
    }

    const tokenState = () => {
      const token = localStorage.getItem('token') || ''
      const exp = parseJwtExp(token)
      setTokenExpiry(exp)
      const state = !token ? 'auth_missing' : (exp && exp <= Math.floor(Date.now() / 1000) ? 'auth_expired' : 'ok')
      dlog('token state', state, exp)
      return { token, state }
    }

    const buildUrl = (token) => `${url}${url.includes('?') ? '&' : '?'}token=${encodeURIComponent(token || '')}`

    const connect = () => {
      if (stopped) return
      const { token, state } = tokenState()
      if (state !== 'ok') {
        transition(state)
        setStatus(state)
        setConnected(false)
        setError(state)
        scheduleReconnect(5000)
        return
      }

      transition('connecting')
      setStatus('connecting')
      setConnected(false)
      setError(null)

      const es = new EventSource(buildUrl(token))
      esRef.current = es
      setReadyState(es.readyState)

      es.onopen = () => {
        const ts = new Date().toISOString()
        dlog('onopen', ts)
        setLastOnOpenAt(ts)
        transition('connected', { ts })
        setStatus('connected')
        setConnected(true)
        setError(null)
        setReadyState(es.readyState)
      }

      es.onmessage = (e) => {
        const ts = new Date().toISOString()
        setLastOnMessageAt(ts)
        try {
          const parsed = JSON.parse(e.data)
          if (parsed?.type === 'heartbeat') setLastHeartbeatAt(ts)
        } catch {}
        dlog('onmessage', e.data)
        setEvents((prev) => [e.data, ...prev].slice(0, 30))
        setStatus('connected')
        setConnected(true)
        setError(null)
        setReadyState(es.readyState)
      }

      es.onerror = () => {
        dlog('onerror')
        es.close()
        setReadyState(es.readyState)
        const nowState = tokenState().state
        setConnected(false)
        if (nowState === 'ok') {
          transition('error')
          setStatus('error')
          setError('stream_error')
          scheduleReconnect(3000)
        } else {
          transition(nowState)
          setStatus(nowState)
          setError(nowState)
          scheduleReconnect(5000)
        }
      }
    }

    connect()
    const iv = setInterval(() => setReadyState(esRef.current ? esRef.current.readyState : null), 1000)

    return () => {
      stopped = true
      clearRetry()
      clearInterval(iv)
      esRef.current?.close()
    }
  }, [url])

  return { status, connected, error, events, tokenExpiry, lastOnOpenAt, lastOnMessageAt, lastHeartbeatAt, reconnectCount, readyState }
}
