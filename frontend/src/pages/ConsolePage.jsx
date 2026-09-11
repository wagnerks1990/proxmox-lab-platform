import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import RFB from '@novnc/novnc'

export default function ConsolePage() {
  const { id } = useParams()
  const screen = useRef(null)
  const [state, setState] = useState('connecting')
  const [fullscreen, setFullscreen] = useState(false)
  const [fullscreenError, setFullscreenError] = useState('')

  useEffect(() => {
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const organizationId = localStorage.getItem('organization_id') || ''
    const url = `${scheme}://${window.location.host}/api/vms/${id}/console/novnc/ws?organization_id=${encodeURIComponent(organizationId)}`
    const rfb = new RFB(screen.current, url)
    rfb.scaleViewport = true
    rfb.resizeSession = true
    rfb.addEventListener('connect', () => setState('connected'))
    rfb.addEventListener('disconnect', event => setState(event.detail.clean ? 'closed' : 'failed'))
    rfb.addEventListener('credentialsrequired', () => setState('credentials required'))
    return () => rfb.disconnect()
  }, [id])

  useEffect(() => {
    const updateFullscreen = () => setFullscreen(document.fullscreenElement === screen.current)
    document.addEventListener('fullscreenchange', updateFullscreen)
    return () => document.removeEventListener('fullscreenchange', updateFullscreen)
  }, [])

  const toggleFullscreen = async () => {
    setFullscreenError('')
    try {
      if (document.fullscreenElement) await document.exitFullscreen()
      else if (screen.current?.requestFullscreen) await screen.current.requestFullscreen()
      else setFullscreenError('Full screen is not supported by this browser.')
    } catch { setFullscreenError('The browser could not enter full screen.') }
  }

  return <section className='page-shell console-page' aria-labelledby='console-title'>
    <header className='ui-page-header console-toolbar'>
      <div><p className='muted'>Remote access</p><h2 id='console-title'>VM console</h2><p className='ui-page-header__description'>Click or tap the console before sending keyboard input.</p></div>
      <div className='ui-page-header__actions'><Link className='ui-button ui-button--secondary' to='/vms'>Back to VMs</Link><button type='button' onClick={toggleFullscreen} aria-pressed={fullscreen}>{fullscreen ? 'Exit full screen' : 'Full screen'}</button></div>
    </header>
    <p className='muted' role='status' aria-live='polite'>Connection: <strong>{state}</strong></p>
    {fullscreenError ? <p className='msg error' role='alert'>{fullscreenError}</p> : null}
    <p className='muted'>Proxmox tickets remain on the server and are never placed in the browser URL.</p>
    <div ref={screen} className='console-surface' role='application' aria-label={`Remote graphical console for virtual machine ${id}`} tabIndex='0' />
    <p className='ui-field__hint'>The remote graphical desktop may not expose its contents to assistive technology. Use the guest operating system's accessibility tools where available.</p>
  </section>
}
