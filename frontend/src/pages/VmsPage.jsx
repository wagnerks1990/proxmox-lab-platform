import { useEffect, useState } from 'react'
import api from '../services/api'

const b={marginRight:8,marginBottom:6}
const colors={running:'#198754',stopped:'#6c757d',error:'#dc3545',provisioning:'#ffc107'}

export default function VmsPage({ setMessage }) {
  const [vms,setVms]=useState([])
  const [busy,setBusy]=useState({})
  const load=()=>api.get('/vms').then(r=>setVms(r.data))
  useEffect(()=>{load()},[])
  const act=async(vm,a)=>{setBusy(p=>({...p,[vm.id]:true})); try{if(a==='delete'){if(!confirm('Delete VM?')) return; await api.delete(`/vms/${vm.id}`)}else if(a==='status'){await api.get(`/vms/${vm.id}/status`)}else await api.post(`/vms/${vm.id}/${a}`); await load(); setMessage({type:'success',text:`${a} successful`})}catch(e){setMessage({type:'error',text:JSON.stringify(e?.response?.data?.detail||'Action failed')})} finally{setBusy(p=>({...p,[vm.id]:false}))}}
  const conn=async(vm,p)=>{try{const r=await api.get(`/vms/${vm.id}/console/${p}`); if(p==='ttyd'||p==='terminal-url'){window.open(r.data.url,'_blank')} if(p==='rdp'){const blob=new Blob([r.data.rdp_file||''],{type:'application/rdp'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`vm-${vm.vmid}.rdp`;a.click()} }catch(e){setMessage({type:'error',text:JSON.stringify(e?.response?.data?.detail||'Connect failed')})}}
  return <div><h3>My VMs</h3><table><thead><tr><th>Name</th><th>VMID</th><th>Status</th><th>Node</th><th>IP</th><th>Actions</th><th>Connect</th></tr></thead><tbody>{vms.map(v=><tr key={v.id}><td>{v.vm_name}</td><td>{v.vmid}</td><td><span style={{background:colors[v.status]||'#777',color:'#fff',padding:'2px 8px',borderRadius:10}}>{v.status}</span></td><td>{v.proxmox_node}</td><td>{v.assigned_ip||'-'}</td><td><button style={b} disabled={busy[v.id]} onClick={()=>act(v,'start')}>Start</button><button style={b} disabled={busy[v.id]} onClick={()=>act(v,'stop')}>Stop</button><button style={b} disabled={busy[v.id]} onClick={()=>act(v,'reboot')}>Reboot</button><button style={b} disabled={busy[v.id]} onClick={()=>act(v,'delete')}>Delete</button><button style={b} disabled={busy[v.id]} onClick={()=>act(v,'status')}>Refresh</button></td><td>{v.ssh_enabled&&v.assigned_ip?<button style={b} onClick={()=>conn(v,'ttyd')}>Web Terminal</button>:null}{v.console_enabled?<button style={b} onClick={()=>conn(v,'novnc')}>Console</button>:null}{v.rdp_enabled?<button style={b} onClick={()=>conn(v,'rdp')}>RDP</button>:null}{v.spice_enabled?<button style={b} onClick={()=>conn(v,'spice')}>SPICE</button>:null}</td></tr>)}</tbody></table></div>
}
