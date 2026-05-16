import StatusBadge from './StatusBadge'

export default function VmDetailsDrawer({ vm, onClose, user }) {
  if (!vm) return null
  return <div className='drawer-backdrop' onClick={onClose}><aside className='drawer' onClick={e => e.stopPropagation()}>
    <div className='drawer-head'><h3>{vm.vm_name}</h3><button className='btn ghost' onClick={onClose}>Close</button></div>
    <div className='tabs'><span>Overview</span><span>Console</span><span>Network</span><span>Activity</span><span>Settings</span></div>
    <div className='panel'><div>VMID: {vm.vmid}</div><div>Status: <StatusBadge status={vm.status} /></div><div>Node: {vm.proxmox_node}</div><div>Assigned IP: {vm.assigned_ip || '-'}</div><div>Discovered IP: {vm.discovered_ip || '-'}</div><div>Effective IP: {vm.ip || vm.assigned_ip || vm.discovered_ip || '-'}</div><div>Hostname: {vm.hostname || '-'}</div><div>Protocols: {vm.access_protocols || '-'}</div><div>Created: {vm.created_at || '-'}</div><div>Owner: {(user?.role==='Admin'||user?.role==='Teacher') ? (vm.owner_id||'-') : 'N/A'}</div></div>
  </aside></div>
}
