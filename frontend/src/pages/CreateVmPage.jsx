import { useEffect, useState } from 'react'
import api from '../services/api'

export default function CreateVmPage({ setMessage }) {
  const [templates,setTemplates]=useState([])
  const [templateId,setTemplateId]=useState('')
  const [labName,setLabName]=useState('linuxlab')
  useEffect(()=>{api.get('/templates').then(r=>{setTemplates(r.data); if(r.data[0]) setTemplateId(r.data[0].id)})},[])
  const create=async()=>{try{const r=await api.post('/vms',{template_id:Number(templateId),lab_name:labName,auto_start:true}); setMessage({type:'success',text:r.data.message||'Created'})}catch(e){setMessage({type:'error',text:JSON.stringify(e?.response?.data?.detail||'Create failed')})}}
  return <div className='panel'><h3>Create VM</h3><p style={{color:'#a7b0d6'}}>Pick template and lab name to provision a VM.</p><select className='input' value={templateId} onChange={e=>setTemplateId(e.target.value)}>{templates.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select><input className='input' value={labName} onChange={e=>setLabName(e.target.value)} placeholder='Lab name' /><button onClick={create}>Create VM</button></div>
}
