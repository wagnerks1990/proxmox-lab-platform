export default function MessageBanner({ message }) {
  if (!message) return null
  return <div style={{ color: message.type === 'error' ? '#b00020' : '#0a7a2f', padding: 8 }}>{message.text}</div>
}
