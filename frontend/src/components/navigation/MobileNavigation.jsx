import { useEffect, useRef } from 'react'
import BrandLockup from './BrandLockup'
import NavIcon from './NavIcon'
import NavigationLinks from './NavigationLinks'

const focusableSelector = 'a[href], button:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

export default function MobileNavigation({ access, open, onClose, returnFocusRef }) {
  const drawerRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const drawer = drawerRef.current
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    drawer?.querySelector(focusableSelector)?.focus()

    const onKeyDown = event => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }
      if (event.key !== 'Tab' || !drawer) return
      const focusable = [...drawer.querySelectorAll(focusableSelector)]
      if (!focusable.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', onKeyDown)
      returnFocusRef.current?.focus()
    }
  }, [open, onClose, returnFocusRef])

  if (!open) return null
  return <div className='mobile-drawer-layer'>
    <button className='mobile-drawer-backdrop' type='button' onClick={onClose} aria-label='Close navigation'/>
    <aside className='mobile-drawer' id='mobile-navigation-drawer' ref={drawerRef} aria-label='Mobile navigation' aria-modal='true' role='dialog'>
      <div className='mobile-drawer-header'>
        <BrandLockup onNavigate={onClose}/>
        <button className='icon-button' type='button' onClick={onClose} aria-label='Close navigation'><NavIcon name='close'/></button>
      </div>
      <NavigationLinks access={access} onNavigate={onClose}/>
    </aside>
  </div>
}
