import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import RFB from '@novnc/novnc'

export default function ConsolePage() {
  const { id } = useParams()
  const screen = useRef(null)
  const [state, setState] = useState('connecting')

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

  return <section className='panel'><h2>VM console</h2><p className='muted'>Connection: {state}. Proxmox tickets remain on the server and are never placed in the browser URL.</p><div ref={screen} style={{height:'70vh',background:'#000',overflow:'hidden'}} /></section>
}
