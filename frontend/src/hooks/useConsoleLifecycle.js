import { useState } from 'react'

export default function useConsoleLifecycle() {
  const [status, setStatus] = useState('idle')
  return { status, setStatus }
}
