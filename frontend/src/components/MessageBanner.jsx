import { normalizeMessage } from './message'

export default function MessageBanner({ message }) {
  const normalized = normalizeMessage(message)
  if (!normalized) return null
  return <div className={`msg ${normalized.type}`} role={normalized.type === 'error' ? 'alert' : 'status'} aria-live='polite'>{normalized.text}</div>
}
