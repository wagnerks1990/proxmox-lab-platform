import { useState } from 'react'

export default function useReconnectToken() {
  const [token, setToken] = useState(null)
  return { reconnectToken: token, setReconnectToken: setToken }
}
