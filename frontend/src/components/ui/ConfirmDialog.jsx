import { useEffect, useId, useRef } from 'react'
import Button from './Button'

export default function ConfirmDialog({ open, title, children, confirmLabel = 'Confirm', cancelLabel = 'Cancel', tone = 'danger', busy = false, onConfirm, onCancel }) {
  const cancelRef = useRef(null)
  const dialogRef = useRef(null)
  const titleId = `confirm-${useId().replaceAll(':', '')}`

  useEffect(() => {
    if (!open) return undefined
    const previousFocus = document.activeElement
    cancelRef.current?.focus()
    const handleKeyDown = event => {
      if (event.key === 'Escape' && !busy) onCancel?.()
      if (event.key !== 'Tab') return
      const focusable = dialogRef.current?.querySelectorAll('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])') || []
      if (!focusable.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      previousFocus?.focus?.()
    }
  }, [busy, onCancel, open])

  if (!open) return null
  return <div className='ui-dialog-backdrop' role='presentation' onMouseDown={event => {
    if (event.target === event.currentTarget && !busy) onCancel?.()
  }}>
    <section ref={dialogRef} className='ui-dialog' role='alertdialog' aria-modal='true' aria-labelledby={titleId}>
      <header className='ui-dialog__header'><h2 id={titleId}>{title}</h2></header>
      <div className='ui-dialog__body'>{children}</div>
      <footer className='ui-dialog__actions'>
        <Button ref={cancelRef} variant='secondary' disabled={busy} onClick={onCancel}>{cancelLabel}</Button>
        <Button variant={tone} busy={busy} onClick={onConfirm}>{confirmLabel}</Button>
      </footer>
    </section>
  </div>
}
