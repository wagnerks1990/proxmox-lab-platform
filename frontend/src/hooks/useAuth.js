import { useCallback, useEffect, useState } from 'react'
import api from '../services/api'

export default function useAuth() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [initialized, setInitialized] = useState(false)
  const [authError, setAuthError] = useState(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setAuthError(null)
    const token = localStorage.getItem('token')
    console.log('[auth] refresh:start', { hasToken: !!token })
    if (!token) {
      setUser(false)
      setLoading(false)
      setInitialized(true)
      console.log('[auth] refresh:no-token')
      return false
    }
    try {
      const r = await api.get('/auth/me')
      setUser(r.data)
      console.log('[auth] refresh:ok', r.data)
      return r.data
    } catch (err) {
      console.error('[auth] refresh:failed', err?.response?.status, err?.response?.data || err)
      localStorage.removeItem('token')
      setUser(false)
      setAuthError(err?.response?.data?.detail || 'Session validation failed')
      return false
    } finally {
      setLoading(false)
      setInitialized(true)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  return { user, setUser, loading, refresh, initialized, authError }
}
