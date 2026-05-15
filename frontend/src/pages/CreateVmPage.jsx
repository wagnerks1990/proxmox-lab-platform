import { useEffect, useState } from 'react'
import api from '../services/api'

export default function CreateVmPage({ setMessage }) {
  const [templates,setTemplates]=useState([])
  const [templateId,setTemplateId]=useState('')
  const [labName,setLabName]=useState('linuxlab')
  useEffect(()=>{api.get('/templates').then(r=>{setTemplates(r.data); if(r.data[0]) setTemplateId(r.data[0].id)})},[])
  const create=async()=>{try{const r=await api.post('/vms',{template_id:Number(templateId),lab_name:labName,auto_start:true}); setMessage({type:'success',text:r.data.message||'Created'})}catch(e){setMessage({type:'error',text:JSON.stringify(e?.response?.data?.detail||'Create failed')})}}
  return <div><h3>Create VM</h3><select value={templateId} onChange={e=>setTemplateId(e.target.value)}>{templates.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select><input value={labName} onChange={e=>setLabName(e.target.value)} /><button onClick={create}>Create</button></div>
}
