const STATE_TONES = {
  active: 'success', healthy: 'success', ok: 'success', pass: 'success', passed: 'success', ready: 'success', running: 'success', succeeded: 'success', verified: 'success',
  degraded: 'warning', partial: 'warning', warn: 'warning', warning: 'warning',
  cancelled: 'neutral', closed: 'neutral', disabled: 'neutral', draft: 'neutral', inactive: 'neutral', stopped: 'neutral', unknown: 'neutral',
  connecting: 'info', pending: 'info', provisioning: 'info', queued: 'info', reconnecting: 'info', running_job: 'info', scheduled: 'info',
  blocked: 'danger', error: 'danger', expired: 'danger', fail: 'danger', failed: 'danger', missing: 'danger', offline: 'danger', revoked: 'danger',
}

export default function StatusBadge({ status, tone, label, className = '' }) {
  const normalized = String(status || 'unknown').trim().toLowerCase().replaceAll(' ', '_')
  const resolvedTone = tone || STATE_TONES[normalized] || 'neutral'
  return <span className={`ui-status-badge ui-status-badge--${resolvedTone} ${className}`.trim()}>
    {label || status || 'Unknown'}
  </span>
}
