export default function MessageBanner({ message }) {
  if (!message) return null
  return <div className={`msg ${message.type === 'error' ? 'error' : 'success'}`}>{message.text}</div>
}
