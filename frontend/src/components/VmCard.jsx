import StatusBadge from './StatusBadge'
import ProtocolButton from './ProtocolButton'

export default function VmCard({ vm, onAction, onLaunch, loading, isAdmin }) {
  const has = p => (vm.access_protocols || '').split(',').map(x => x.trim().toLowerCase()).includes(p)
  const protocols = [
    { key: 'guacamole', label: 'Open Console', enabled: true, reason: 'Guacamole unavailable' },
    { key: 'console', label: 'noVNC (future)', enabled: false, reason: 'not implemented yet' },
    { key: 'web_terminal', label: 'Web Terminal', enabled: vm.ssh_enabled && has('ssh'), reason: 'SSH not enabled' },
    { key: 'rdp', label: 'RDP (Guacamole)', enabled: vm.rdp_enabled && has('rdp'), reason: 'RDP not enabled' },
    { key: 'spice', label: 'SPICE', enabled: vm.spice_enabled && has('spice'), reason: 'SPICE not enabled' },
  ]
  return <div className='vm-card'>
    <div className='vm-head'><div className='vm-os'>🖥️</div><div><div className='vm-name'>{vm.vm_name}</div><div className='muted'>VMID {vm.vmid} · {vm.proxmox_node}</div></div><StatusBadge status={vm.status} /></div>
    <div className='muted'>IP {vm.ip || vm.assigned_ip || vm.discovered_ip || '-'} · Host {vm.hostname || '-'}</div>
    {isAdmin ? <div className='muted'>Owner ID: {vm.owner_id || '-'}</div> : null}
    <div className='group'>{protocols.map(p => <ProtocolButton key={p.key} label={p.label} enabled={p.enabled} reason={p.reason} loading={loading} onClick={() => onLaunch(vm, p.key)} />)}</div>
    <div className='group'><button className='btn' disabled={loading} onClick={() => onAction(vm, 'start')}>Start</button><button className='btn' disabled={loading} onClick={() => onAction(vm, 'stop')}>Stop</button><button className='btn' disabled={loading} onClick={() => onAction(vm, 'reboot')}>Reboot</button><button className='btn danger' disabled={loading} onClick={() => onAction(vm, 'delete')}>Delete</button><button className='btn ghost' disabled={loading} onClick={() => onAction(vm, 'status')}>Refresh</button></div>
  </div>
}
