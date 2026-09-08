import { useEffect, useState } from 'react'
import api from '../services/api'
import useSessionHeartbeat from '../hooks/useSessionHeartbeat'
import useConsoleLifecycle from '../hooks/useConsoleLifecycle'
import useReconnectToken from '../hooks/useReconnectToken'
import ConsoleLaunchOverlay from '../components/console/ConsoleLaunchOverlay'
import ConsoleStatusBanner from '../components/console/ConsoleStatusBanner'
import ReconnectBanner from '../components/console/ReconnectBanner'
import SessionExpiredNotice from '../components/console/SessionExpiredNotice'

const statusClass = (s) => `badge ${s==='running'?'badge-running':s==='stopped'?'badge-stopped':s==='provisioning'?'badge-provisioning':'badge-error'}`
const hasAccessProtocol = (vm, protocol) => vm.access_protocols ? vm.access_protocols.split(',').map(x => x.trim().toLowerCase()).includes(protocol) : false

export default function VmsPage({ setMessage }) {
  const [vms, setVms] = useState([])
  const [busy, setBusy] = useState({})
  const [launching, setLaunching] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [reconBusy, setReconBusy] = useState(false)
  const [reconSummary, setReconSummary] = useState(null)
  const { status, setStatus } = useConsoleLifecycle()
  const { setReconnectToken } = useReconnectToken()
  useSessionHeartbeat(sessionId, !!sessionId && !['expired','failed'].includes(status), 30000)

  const load = () => api.get('/vms').then(r => setVms(Array.isArray(r.data) ? r.data : [])).catch(() => setVms([]))
  const reconcile = async () => { setReconBusy(true); try { const r = await api.get('/admin/proxmox/reconciliation/vms'); setReconSummary(r.data?.summary || null); await load(); setMessage({ type: 'success', text: 'Reconciliation completed.' }) } catch (e) { setMessage({ type: 'error', text: JSON.stringify(e?.response?.data?.detail || 'Reconcile failed') }) } finally { setReconBusy(false) } }
  useEffect(() => { load() }, [])

  const act = async (vm, a) => { setBusy(p => ({ ...p, [vm.id]: true })); try { if (a === 'delete') { if (!confirm('Delete VM?')) return; await api.delete(`/vms/${vm.id}`) } else if (a === 'remove_app_record') { if (!confirm('Remove only the Lab Control app record? This will not delete any Proxmox VM.')) return; await api.delete(`/admin/lab-vms/${vm.id}/app-record`) } else if (a === 'status') { await api.get(`/vms/${vm.id}/status`) } else { await api.post(`/vms/${vm.id}/${a}`) } await load(); setMessage({ type: 'success', text: `${a.toUpperCase()} action completed.` }) } catch (e) { setMessage({ type: 'error', text: JSON.stringify(e?.response?.data?.detail || 'Action failed') }) } finally { setBusy(p => ({ ...p, [vm.id]: false })) } }

  const launch = async (vm, protocol) => {
    if (launching) return
    setLaunching(true); setStatus('launching')
    try {
      if (protocol === 'web_terminal') { const r = await api.get(`/vms/${vm.id}/console/terminal-url`); setSessionId(r.data?.session_id || null); setReconnectToken(r.data?.reconnect_token || null); window.open(r.data.url, '_blank', 'noopener,noreferrer'); setStatus('connected'); return }
      if (protocol === 'rdp') { const r = await api.get(`/vms/${vm.id}/console/rdp`); const blob = new Blob([r.data.rdp_file || ''], { type: 'application/rdp' }); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `vm-${vm.vmid}.rdp`; a.click(); setStatus('connected'); return }
      if (protocol === 'spice') { await api.get(`/vms/${vm.id}/console/spice`); setMessage({ type: 'success', text: 'SPICE config generated.' }); setStatus('connected'); return }
      if (protocol === 'console') { const r = await api.get(`/vms/${vm.id}/console/novnc`); setSessionId(r.data?.session_id || null); setReconnectToken(r.data?.reconnect_token || null); if (r.data?.novnc_url) window.open(r.data.novnc_url, '_blank', 'noopener,noreferrer'); setStatus('connected') }
    } catch (e) { setStatus('failed'); setMessage({ type: 'error', text: JSON.stringify(e?.response?.data?.detail || 'Connection launch failed') }) } finally { setLaunching(false) }
  }

  return <section className='panel'>
    <ConsoleLaunchOverlay show={launching} /><ConsoleStatusBanner status={status} /><ReconnectBanner status={status} /><SessionExpiredNotice status={status} />
    <div className='panel-head'><h3>My Lab VMs</h3><button disabled={reconBusy} onClick={reconcile}>Refresh/Reconcile</button><p className='muted'>Lifecycle management and protocol access for app-managed lab VMs.</p><p className='muted'>Need raw Proxmox inventory? Use Admin → Proxmox Inventory.</p></div>
    {reconSummary ? <p className='muted'>Reconcile summary: app_vms={reconSummary.app_vms}, matched={reconSummary.matched}, missing={reconSummary.missing}, status_updated={reconSummary.status_updated}, proxmox_only={reconSummary.proxmox_only}</p> : null}
    {vms.length === 0 ? <p className='muted'>No lab-managed VMs yet. Import templates and use Create VM.</p> : null}
    <table className='vm-table'><thead><tr><th>VM</th><th>Status</th><th>Node</th><th>IP</th><th>Actions</th><th>Connections</th></tr></thead><tbody>
      {vms.map(v => { const missing = v.status==='missing' || v.status==='error'; const canTerminal = !missing && v.allowed_terminal!==false && v.ssh_enabled && hasAccessProtocol(v, 'ssh') && !!v.assigned_ip; const canConsole = !missing && v.allowed_console!==false && v.console_enabled && hasAccessProtocol(v, 'novnc'); const canRdp = !missing && v.allowed_rdp!==false && v.rdp_enabled && hasAccessProtocol(v, 'rdp'); const canSpice = !missing && v.allowed_spice!==false && v.spice_enabled && hasAccessProtocol(v, 'spice'); return <tr key={v.id}><td><div className='vm-title'>{v.vm_name}</div><div className='muted'>VMID {v.vmid}</div>{v.assignment_expires_at?<div className='muted'>Access ends {new Date(v.assignment_expires_at).toLocaleString()}</div>:null}</td><td><span className={statusClass(v.status)}>{v.status}</span>{v.status==='missing'?<div className='muted'>Missing in Proxmox. This app record exists, but the VM was not found on the configured Proxmox cluster.</div>:null}</td><td>{v.proxmox_node}</td><td>{v.assigned_ip || '-'}</td><td><div className='group'><button disabled={busy[v.id] || missing} onClick={() => act(v, 'start')}>Start</button><button disabled={busy[v.id] || missing || v.allowed_stop===false} onClick={() => act(v, 'stop')}>Stop</button><button disabled={busy[v.id] || missing} onClick={() => act(v, 'reboot')}>Reboot</button>{v.allowed_delete!==false?<button className='btn-danger' disabled={busy[v.id]} onClick={() => act(v, 'delete')}>Delete</button>:null}<button disabled={busy[v.id]} onClick={() => act(v, 'status')}>Refresh</button>{missing && v.allowed_delete!==false?<button className='btn-danger' disabled={busy[v.id]} onClick={() => act(v, 'remove_app_record')}>Remove app record</button>:null}</div></td><td><div className='group connection-group'>{canTerminal ? <button className='btn-connection' disabled={launching} onClick={() => launch(v, 'web_terminal')}>WEB TERMINAL</button> : null}{canConsole ? <button className='btn-connection' disabled={launching} onClick={() => launch(v, 'console')}>Console</button> : null}{canRdp ? <button className='btn-connection' disabled={launching} onClick={() => launch(v, 'rdp')}>RDP</button> : null}{canSpice ? <button className='btn-connection' disabled={launching} onClick={() => launch(v, 'spice')}>SPICE</button> : null}</div></td></tr> })}
    </tbody></table>
  </section>
}
