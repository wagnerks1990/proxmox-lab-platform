import { useCallback, useEffect, useState } from 'react'
import api from '../services/api'
import { classifyAuthFailure } from '../auth/authState'

export default function useAuth() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get('/auth/me')
      setUser(response.data)
    } catch (requestError) {
      const next = classifyAuthFailure(requestError)
      setUser(next.user)
      setError(next.error)
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => {
    refresh()
    const unauthorized = () => { setError(null); setUser(false); setLoading(false) }
    window.addEventListener('auth:unauthorized', unauthorized)
    return () => window.removeEventListener('auth:unauthorized', unauthorized)
  }, [refresh])

  return { user, setUser, loading, error, refresh }
}

export function clearAuth(){}
