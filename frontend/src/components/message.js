function stringify(value) {
  if (typeof value === 'string') return value
  if (value instanceof Error) return value.message
  try { return JSON.stringify(value) } catch { return String(value) }
}

export function normalizeMessage(message) {
  if (message === null || message === undefined || message === '') return null
  if (typeof message === 'string') return { type: 'success', text: message }

  const type = message?.type === 'error' ? 'error' : 'success'
  const value = message?.text ?? message?.detail ?? message?.message ?? message
  return { type, text: stringify(value) }
}
