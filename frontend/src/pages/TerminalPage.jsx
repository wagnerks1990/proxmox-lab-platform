import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import Alert from '../components/ui/Alert'
import Card, { CardHeader } from '../components/ui/Card'
import StatusBadge from '../components/ui/StatusBadge'

export default function TerminalPage({ enabled = false }) {
  const { id } = useParams()
  const container = useRef(null)
  const [state, setState] = useState('connecting')

  useEffect(() => {
    if (!enabled) return undefined
    const terminal = new Terminal({ cursorBlink: true, convertEol: true, theme: { background: '#080b16' } })
    const fit = new FitAddon()
    terminal.loadAddon(fit)
    terminal.open(container.current)
    const fitTerminal = () => {
      try { fit.fit() } catch { /* The container may be between layouts. */ }
    }
    const initialFit = window.requestAnimationFrame(fitTerminal)
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const organizationId = localStorage.getItem('organization_id') || ''
    const socket = new WebSocket(`${scheme}://${window.location.host}/api/vms/${id}/console/ssh/ws?organization_id=${encodeURIComponent(organizationId)}`)
    socket.onopen = () => setState('connected')
    socket.onmessage = event => terminal.write(event.data)
    socket.onerror = () => setState('failed')
    socket.onclose = event => setState(current => current === 'failed' || event.code !== 1000 ? 'failed' : 'closed')
    const disposable = terminal.onData(data => { if (socket.readyState === WebSocket.OPEN) socket.send(data) })
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(fitTerminal)
    observer?.observe(container.current)
    window.addEventListener('resize', fitTerminal)
    return () => { window.cancelAnimationFrame(initialFit); observer?.disconnect(); disposable.dispose(); socket.close(); terminal.dispose(); window.removeEventListener('resize', fitTerminal) }
  }, [enabled, id])

  if (!enabled) return <Card>
    <CardHeader title='SSH terminal unavailable' />
    <Alert tone='warning' title='This connection method is disabled'>Use an approved console option from My Lab VMs. SSH terminal access remains unavailable until the server and interface explicitly enable the hardened feature.</Alert>
  </Card>

  return <Card>
    <CardHeader title='SSH terminal' description='Host identity is verified against the server-side known-hosts file.' actions={<span role='status' aria-live='polite'><StatusBadge status={state} /></span>} />
    {state === 'failed' ? <Alert tone='error' title='Terminal connection failed'>Return to My Lab VMs and use an approved connection method. SSH terminal access is disabled unless the server explicitly enables the hardened feature.</Alert> : null}
    <div ref={container} className='terminal-surface' aria-label='SSH terminal session' />
  </Card>
}
