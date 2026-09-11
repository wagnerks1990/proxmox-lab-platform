import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { EmptyState, ErrorState, LoadingState } from '../components/workflows/WorkflowState'
import WorkflowStatus from '../components/workflows/WorkflowStatus'
import api from '../services/api'

const terminalStates = new Set(['succeeded', 'failed', 'cancelled'])
const protocols = vm => (vm.access_protocols || '').split(',').map(value => value.trim().toLowerCase())
const errorDetail = error => {
  const detail = error?.response?.data?.detail
  return typeof detail === 'string' ? detail : JSON.stringify(detail || error?.message || 'Action failed')
}

export default function VmsPage({ setMessage }) {
  const [vms, setVms] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState({})

  const load = useCallback(async ({ quiet = false } = {}) => {
    if (!quiet) setLoading(true)
    setError('')
    try {
      const response = await api.get('/vms')
      setVms(Array.isArray(response.data) ? response.data : [])
    } catch (requestError) {
      setError(errorDetail(requestError))
    } finally {
      if (!quiet) setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

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
    throw new Error('This operation is still running. Check Operations for progress.')
  }

  const act = async (vm, action) => {
    setBusy(previous => ({ ...previous, [vm.id]: action }))
    try {
      let response
      if (action === 'delete') {
        const preview = (await api.get(`/vms/${vm.id}/delete-preview`)).data
        if (!window.confirm(`Delete ${preview.vm_name} (VMID ${preview.vmid}) from Proxmox? Its history will be retained after deletion is verified.`)) return
        response = await api.delete(`/vms/${vm.id}`, { params: { confirmation: preview.confirmation } })
      } else if (action === 'status') response = await api.get(`/vms/${vm.id}/status`)
      else response = await api.post(`/vms/${vm.id}/${action}`)
      await waitForOperation(response?.data?.operation_id)
      await load({ quiet: true })
      setMessage({ type: 'success', text: action === 'status' ? `${vm.vm_name} status refreshed.` : `${vm.vm_name}: ${action} completed.` })
    } catch (requestError) {
      setMessage({ type: 'error', text: errorDetail(requestError) })
    } finally {
      setBusy(previous => ({ ...previous, [vm.id]: null }))
    }
  }

  const launch = async (vm, protocol) => {
    setBusy(previous => ({ ...previous, [vm.id]: protocol }))
    try {
      if (protocol === 'rdp') {
        const response = await api.get(`/vms/${vm.id}/console/rdp`)
        const blob = new Blob([response.data.rdp_file || ''], { type: 'application/rdp' })
        const link = document.createElement('a')
        link.href = URL.createObjectURL(blob)
        link.download = `vm-${vm.vmid}.rdp`
        link.click()
        URL.revokeObjectURL(link.href)
        return
      }
      const response = await api.get(`/vms/${vm.id}/console/novnc`)
      if (!response.data?.launch_url) throw new Error('Console launch URL was not returned')
      window.open(response.data.launch_url, '_blank', 'noopener,noreferrer')
    } catch (requestError) {
      setMessage({ type: 'error', text: errorDetail(requestError) })
    } finally {
      setBusy(previous => ({ ...previous, [vm.id]: null }))
    }
  }

  if (loading) return <LoadingState label='Loading your virtual machines…' />
  if (error && !vms.length) return <ErrorState message={error} onRetry={load} retrying={loading} />

  return <section>
    <div className='panel-head'>
      <div><h1>My virtual machines</h1><p className='muted'>Connect to a running machine or manage its power state.</p></div>
      <Link className='btn' to='/create'>Provision a VM</Link>
    </div>
    {error ? <p className='msg error' role='alert'>{error}</p> : null}
    {!vms.length ? <EmptyState title='No virtual machines yet' message='When a classroom assignment is available, provision it here.' action={<Link to='/create'>View available assignments</Link>} /> : null}
    <div className='card-grid'>
      {vms.map(vm => {
        const state = String(vm.status || '').toLowerCase()
        const missing = ['missing', 'error'].includes(state)
        const running = state === 'running'
        const stopped = state === 'stopped'
        const allowed = protocols(vm)
        const canConsole = !missing && vm.allowed_console !== false && vm.console_enabled && allowed.includes('novnc')
        const canRdp = !missing && vm.allowed_rdp !== false && vm.rdp_enabled && allowed.includes('rdp')
        const working = Boolean(busy[vm.id])
        return <article className='panel' key={vm.id} aria-busy={working}>
          <div className='panel-head'>
            <div><h3>{vm.vm_name}</h3><WorkflowStatus value={vm.status} /></div>
            <button type='button' onClick={() => act(vm, 'status')} disabled={working} aria-label={`Refresh ${vm.vm_name} status`}>Refresh</button>
          </div>
          {working ? <p className='muted' role='status'>{busy[vm.id] === 'status' ? 'Refreshing status…' : `${busy[vm.id]} in progress…`}</p> : null}
          {missing ? <p className='msg error'>This VM is unavailable. Refresh its status or ask an instructor for help.</p> : null}
          {running && canConsole ? <button type='button' className='btn-connection' disabled={working} onClick={() => launch(vm, 'console')}>Open console</button>
            : running && canRdp ? <button type='button' className='btn-connection' disabled={working} onClick={() => launch(vm, 'rdp')}>Download RDP connection</button>
              : stopped ? <button type='button' disabled={working} onClick={() => act(vm, 'start')}>Start VM</button>
                : <p className='muted'>A connection will be available when this VM is running.</p>}
          <details style={{ marginTop: 14 }}>
            <summary>More actions and details</summary>
            <dl>
              <dt>VMID</dt><dd>{vm.vmid}</dd>
              <dt>Node</dt><dd>{vm.proxmox_node || 'Not assigned'}</dd>
              <dt>Address</dt><dd>{vm.assigned_ip || vm.hostname || 'Not reported'}</dd>
              {vm.assignment_expires_at ? <><dt>Assignment ends</dt><dd>{new Date(vm.assignment_expires_at).toLocaleString()}</dd></> : null}
            </dl>
            <div className='group'>
              {!running && !missing && !stopped ? <button type='button' disabled={working} onClick={() => act(vm, 'start')}>Start</button> : null}
              {running && vm.allowed_stop !== false ? <button type='button' disabled={working} onClick={() => act(vm, 'stop')}>Stop</button> : null}
              {running ? <button type='button' disabled={working} onClick={() => act(vm, 'reboot')}>Reboot</button> : null}
              {running && canConsole && canRdp ? <button type='button' disabled={working} onClick={() => launch(vm, 'rdp')}>Download RDP</button> : null}
            </div>
            {vm.allowed_delete !== false ? <details style={{ marginTop: 12 }}>
              <summary>Delete this VM</summary>
              <p className='muted'>Deletion removes the Proxmox VM after a server-verified preview. History is retained.</p>
              <button type='button' className='btn-danger' disabled={working} onClick={() => act(vm, 'delete')}>Delete VM</button>
            </details> : null}
          </details>
        </article>
      })}
    </div>
  </section>
}
