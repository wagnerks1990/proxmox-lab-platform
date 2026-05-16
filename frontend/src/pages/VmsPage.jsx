import { useEffect, useState } from 'react'
import api from '../services/api'
import VmCard from '../components/VmCard'
import VmDetailsDrawer from '../components/VmDetailsDrawer'
import StatusBadge from '../components/StatusBadge'

export default function VmsPage({ setMessage, user }) {
  const [vms, setVms] = useState([])
  const [busy, setBusy] = useState({})
  const [selected, setSelected] = useState(null)

  const load = () => api.get('/vms').then(r => setVms(r.data))
  useEffect(() => { load() }, [])

  const onAction = async (vm, a) => {
    setBusy(p => ({ ...p, [vm.id]: true }))
    try {
      if (a === 'delete') { if (!confirm('Delete VM?')) return; await api.delete(`/vms/${vm.id}`) }
      else if (a === 'status') await api.get(`/vms/${vm.id}/status`)
      else await api.post(`/vms/${vm.id}/${a}`)
      await load(); setMessage({ type: 'success', text: `${a.toUpperCase()} completed.` })
    } catch (e) { setMessage({ type: 'error', text: JSON.stringify(e?.response?.data?.detail || 'Action failed') }) }
    finally { setBusy(p => ({ ...p, [vm.id]: false })) }
  }

  const onLaunch = async (vm, protocol) => {
    try {
      if (protocol === 'web_terminal') { const r = await api.get(`/vms/${vm.id}/console/terminal-url`); window.open(r.data.url, '_blank', 'noopener,noreferrer'); return }
      if (protocol === 'guacamole') { const r = await api.get(`/vms/${vm.id}/console/guacamole`, { params: { protocol: 'rdp' } }); window.location.assign(r.data.launch_url); return }
      if (protocol === 'console') { setMessage({ type: 'error', text: 'noVNC not implemented yet' }); return }
      if (protocol === 'rdp') { const r = await api.get(`/vms/${vm.id}/console/rdp`); const blob = new Blob([r.data.rdp_file || ''], { type: 'application/rdp' }); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `vm-${vm.vmid}.rdp`; a.click(); return }
      if (protocol === 'spice') { await api.get(`/vms/${vm.id}/console/spice`); setMessage({ type: 'success', text: 'SPICE config generated.' }) }
    } catch (e) { const err = e?.response?.data?.detail?.error || e?.response?.data?.detail || 'Connection launch failed'; setMessage({ type: 'error', text: String(err) }) }
  }

  return <section>
    <div className='panel-head'><h2>My Lab VMs</h2></div>
    <div className='vm-grid'>{vms.map(vm => <div key={vm.id} onDoubleClick={() => setSelected(vm)}><VmCard vm={vm} loading={!!busy[vm.id]} onAction={onAction} onLaunch={onLaunch} isAdmin={user?.role !== 'Student'} /></div>)}</div>
    <div className='panel'><h4>Table View</h4><table className='table2'><thead><tr><th>Name</th><th>VMID</th><th>Status</th><th>Node</th><th>IP</th><th>Owner</th><th/></tr></thead><tbody>{vms.map(v=><tr key={v.id}><td>{v.vm_name}</td><td>{v.vmid}</td><td><StatusBadge status={v.status} /></td><td>{v.proxmox_node}</td><td>{v.ip||v.assigned_ip||v.discovered_ip||'-'}</td><td>{(user?.role==='Admin'||user?.role==='Teacher')?(v.owner_id||'-'):'N/A'}</td><td><button className='btn ghost' onClick={()=>setSelected(v)}>Details</button></td></tr>)}</tbody></table></div>
    <VmDetailsDrawer vm={selected} onClose={() => setSelected(null)} user={user} />
  </section>
}
