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
      dlog('schedule reconnect in', ms)
      clearRetry()
      retryRef.current = setTimeout(connect, ms)
    }

    const tokenState = () => {
      const token = localStorage.getItem('token') || ''
      const exp = parseJwtExp(token)
      setTokenExpiry(exp)
      const now = Math.floor(Date.now() / 1000)
      const state = !token ? 'auth_missing' : (exp && exp <= now ? 'auth_expired' : 'ok')
      dlog('token state', { state, exp, now })
      return { token, state }
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

      const sseUrl = buildUrl(token)
      dlog('opening EventSource', sseUrl)
      es = new EventSource(sseUrl)

      es.onopen = () => {
        dlog('onopen')
        setStatus('connected')
        setConnected(true)
        setError(null)
      }

      es.onmessage = (e) => {
        dlog('onmessage', e.data)
        setEvents((prev) => [e.data, ...prev].slice(0, 30))
        setStatus('connected')
        setConnected(true)
        setError(null)
      }

      es.onerror = () => {
        dlog('onerror')
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
      if (evt.key === 'token') {
        dlog('token changed via storage event')
        connect()
      }
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
