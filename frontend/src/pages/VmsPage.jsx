import { useEffect, useState } from 'react'
import api from '../services/api'

const terminalStates = new Set(['succeeded', 'failed', 'cancelled'])
const protocols = vm => (vm.access_protocols || '').split(',').map(value => value.trim().toLowerCase())

export default function VmsPage({ setMessage }) {
  const [vms, setVms] = useState([])
  const [busy, setBusy] = useState({})
  const load = () => api.get('/vms').then(response => setVms(Array.isArray(response.data) ? response.data : [])).catch(() => setVms([]))
  useEffect(() => { load() }, [])

  const waitForOperation = async operationId => {
    if (!operationId) return
    for (let attempt = 0; attempt < 60; attempt += 1) {
      const operation = (await api.get(`/operations/${operationId}`)).data
      const state = String(operation.state).toLowerCase()
      if (terminalStates.has(state)) {
        if (state !== 'succeeded') throw new Error(operation.error || 'Operation failed')
        return
      }
      await new Promise(resolve => setTimeout(resolve, 2000))
    }
    throw new Error('Operation is still running. Check Operations for progress.')
  }

  const act = async (vm, action) => {
    setBusy(previous => ({ ...previous, [vm.id]: true }))
    try {
      let response
      if (action === 'delete') {
        const preview = (await api.get(`/vms/${vm.id}/delete-preview`)).data
        if (!confirm(`Delete ${preview.vm_name} (VMID ${preview.vmid}) from Proxmox and retain its history after verification?`)) return
        response = await api.delete(`/vms/${vm.id}`, { params: { confirmation: preview.confirmation } })
      } else if (action === 'status') response = await api.get(`/vms/${vm.id}/status`)
      else response = await api.post(`/vms/${vm.id}/${action}`)
      await waitForOperation(response?.data?.operation_id)
      await load()
      setMessage({ type: 'success', text: `${action.toUpperCase()} completed.` })
    } catch (error) {
      setMessage({ type: 'error', text: JSON.stringify(error?.response?.data?.detail || error.message || 'Action failed') })
    } finally { setBusy(previous => ({ ...previous, [vm.id]: false })) }
  }

  const launch = async (vm, protocol) => {
    try {
      if (protocol === 'rdp') {
        const response = await api.get(`/vms/${vm.id}/console/rdp`)
        const blob = new Blob([response.data.rdp_file || ''], { type: 'application/rdp' })
        const link = document.createElement('a')
        link.href = URL.createObjectURL(blob); link.download = `vm-${vm.vmid}.rdp`; link.click(); URL.revokeObjectURL(link.href)
        return
      }
      const endpoint = protocol === 'web_terminal' ? 'terminal-url' : 'novnc'
      const response = await api.get(`/vms/${vm.id}/console/${endpoint}`)
      if (!response.data?.launch_url) throw new Error('Console launch URL was not returned')
      window.open(response.data.launch_url, '_blank', 'noopener,noreferrer')
    } catch (error) { setMessage({ type: 'error', text: JSON.stringify(error?.response?.data?.detail || error.message || 'Connection launch failed') }) }
  }

  return <section className='panel'>
    <div className='panel-head'><h3>My Lab VMs</h3><button onClick={load}>Refresh</button><p className='muted'>Lifecycle management and approved access for your assigned lab VMs.</p></div>
    {vms.length === 0 ? <p className='muted'>No assigned VMs are available.</p> : null}
    <table className='vm-table'><thead><tr><th>VM</th><th>Status</th><th>Node</th><th>IP</th><th>Actions</th><th>Connections</th></tr></thead><tbody>
      {vms.map(vm => { const missing = ['missing', 'error'].includes(vm.status); const allowed = protocols(vm); return <tr key={vm.id}><td><div className='vm-title'>{vm.vm_name}</div><div className='muted'>VMID {vm.vmid}</div></td><td>{vm.status}</td><td>{vm.proxmox_node}</td><td>{vm.assigned_ip || '-'}</td><td><div className='group'><button disabled={busy[vm.id] || missing} onClick={() => act(vm, 'start')}>Start</button><button disabled={busy[vm.id] || missing || vm.allowed_stop === false} onClick={() => act(vm, 'stop')}>Stop</button><button disabled={busy[vm.id] || missing} onClick={() => act(vm, 'reboot')}>Reboot</button>{vm.allowed_delete !== false ? <button className='btn-danger' disabled={busy[vm.id]} onClick={() => act(vm, 'delete')}>Delete</button> : null}<button disabled={busy[vm.id]} onClick={() => act(vm, 'status')}>Refresh</button></div></td><td><div className='group connection-group'>{!missing && vm.allowed_terminal !== false && vm.ssh_enabled && allowed.includes('ssh') && vm.assigned_ip ? <button onClick={() => launch(vm, 'web_terminal')}>Web Terminal</button> : null}{!missing && vm.allowed_console !== false && vm.console_enabled && allowed.includes('novnc') ? <button onClick={() => launch(vm, 'console')}>Console</button> : null}{!missing && vm.allowed_rdp !== false && vm.rdp_enabled && allowed.includes('rdp') ? <button onClick={() => launch(vm, 'rdp')}>RDP</button> : null}</div></td></tr> })}
    </tbody></table>
  </section>
}
