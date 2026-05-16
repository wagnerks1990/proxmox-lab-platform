import { useEffect, useState } from 'react'
import api from '../services/api'

export default function useAuth() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const refresh = () => api.get('/auth/me').then(r => setUser(r.data)).catch(() => setUser(false)).finally(() => setLoading(false))
  useEffect(() => { refresh() }, [])

  return { user, setUser, loading, refresh }
}
