import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'

export default function TerminalPage() {
  const { id } = useParams()
  const container = useRef(null)
  const [state, setState] = useState('connecting')

  useEffect(() => {
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
  }, [id])

  return <section className='panel'><h2>SSH terminal</h2><p className='muted'>Connection: {state}. Host identity is verified against the server-side known-hosts file.</p><div ref={container} style={{height:'70vh',background:'#080b16',padding:8}} /></section>
}
