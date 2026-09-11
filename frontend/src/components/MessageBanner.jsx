import { normalizeMessage } from './message'
import Alert from './ui/Alert'

export default function MessageBanner({ message }) {
  const normalized = normalizeMessage(message)
  if (!normalized) return null
  return <Alert tone={normalized.type === 'error' ? 'error' : 'success'}>{normalized.text}</Alert>
}
