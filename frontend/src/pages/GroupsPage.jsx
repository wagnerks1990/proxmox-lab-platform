import { useEffect, useState } from 'react'
import api from '../services/api'
import { listGroups, createGroup, patchGroup, deleteGroup, listGroupMembers, addGroupMember, removeGroupMember, listGroupTemplatePermissions, patchGroupTemplatePermissions } from '../services/adminGroupsApi'

const empty = { name:'', description:'', enabled:true }

export default function GroupsPage(){
  const [rows,setRows]=useState([])
  const [users,setUsers]=useState([])
  const [templates,setTemplates]=useState([])
  const [form,setForm]=useState(empty)
  const [editing,setEditing]=useState(null)
  const [members,setMembers]=useState({})
  const [groupPerms,setGroupPerms]=useState({})
  const [msg,setMsg]=useState('')

  const load = ()=> listGroups().then(setRows).catch(()=>setRows([]))
  useEffect(()=>{ load(); api.get('/admin/users').then(r=>setUsers(Array.isArray(r.data)?r.data:[])).catch(()=>setUsers([])); api.get('/admin/templates').then(r=>setTemplates(Array.isArray(r.data)?r.data:[])).catch(()=>setTemplates([])) },[])

  const save = async ()=> {
    try{
      if(editing) await patchGroup(editing, form); else await createGroup(form)
      setForm(empty); setEditing(null); await load(); setMsg('Group saved.')
    }catch(e){ setMsg(JSON.stringify(e?.response?.data?.detail || 'Save failed'))}
  }

  const loadMembers = async (groupId) => {
    try {
      const memberList = await listGroupMembers(groupId)
      setMembers((prev) => ({ ...prev, [groupId]: memberList }))
    } catch (e) {
      setMsg(JSON.stringify(e?.response?.data?.detail || 'Failed to load group members'))
    }
  }

  const loadTemplatePermissions = async (groupId) => {
    try {
      const perms = await listGroupTemplatePermissions(groupId)
      setGroupPerms((prev) => ({ ...prev, [groupId]: perms.template_ids || [] }))
    } catch (e) {
      setMsg(JSON.stringify(e?.response?.data?.detail || 'Failed to load group template permissions'))
    }
  }

  const removeMember = async (groupId, userId) => {
    try {
      await removeGroupMember(groupId, userId)
      await loadMembers(groupId)
    } catch (e) {
      setMsg(JSON.stringify(e?.response?.data?.detail || 'Failed to remove group member'))
    }
  }

  const addMember = async (groupId, userId) => {
    if (!userId) return
    try {
      await addGroupMember(groupId, { user_id: userId })
      await loadMembers(groupId)
    } catch (e) {
      setMsg(JSON.stringify(e?.response?.data?.detail || 'Failed to add group member'))
    }
  }

  return <section>
    <h2>Groups</h2>
    <p className='muted'>Manage classes/groups, memberships, and group template permissions.</p>
    {msg?<p className='muted'>{msg}</p>:null}
    <div className='panel'><h3>{editing?'Edit Group':'Create Group'}</h3><div className='group'>
      <input className='input' placeholder='Name' value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/>
      <input className='input' placeholder='Description' value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/>
      <label><input type='checkbox' checked={form.enabled} onChange={e=>setForm({...form,enabled:e.target.checked})}/> enabled</label>
      <button onClick={save} disabled={!form.name}>Save</button>
    </div></div>
    {rows.length===0?<p className='muted'>No groups/classes configured yet.</p>:null}
    <table className='vm-table'><thead><tr><th>Name</th><th>Enabled</th><th>Members</th><th>Template perms</th><th>Actions</th></tr></thead><tbody>
      {rows.map(g=><tr key={g.id}><td>{g.name}</td><td>{String(g.enabled)}</td><td>{g.member_count}</td><td>{g.template_permission_count}</td><td><div className='group'>
        <button onClick={()=>{setEditing(g.id); setForm({name:g.name,description:g.description||'',enabled:g.enabled})}}>Edit</button>
        <button onClick={async()=>{await loadMembers(g.id)}}>Members</button>
        <button onClick={async()=>{await loadTemplatePermissions(g.id)}}>Template Permissions</button>
        <button className='btn-danger' onClick={async()=>{if(!confirm('Delete group? This removes memberships/permissions but not users/VMs.')) return; await deleteGroup(g.id); await load()}}>Delete</button>
      </div>
      {Array.isArray(members[g.id])?<div className='panel'><h4>Members</h4><div className='group'>{members[g.id].map(m=><span key={m.user_id}>{m.username||m.user_id} <button onClick={async()=>{await removeMember(g.id,m.user_id)}}>x</button></span>)}</div><select className='input' onChange={async e=>{const uid=Number(e.target.value); await addMember(g.id,uid)}}><option value=''>Add user…</option>{users.map(u=><option key={u.id} value={u.id}>{u.username}</option>)}</select></div>:null}
      {Array.isArray(groupPerms[g.id])?<div className='panel'><h4>Template Permissions</h4>{templates.length===0?<p className='muted'>Import Proxmox templates before assigning template permissions.</p>:null}<div className='group'>{templates.map(t=><label key={t.id}><input type='checkbox' checked={groupPerms[g.id].includes(t.id)} onChange={e=>{const next=e.target.checked?[...groupPerms[g.id],t.id]:groupPerms[g.id].filter(x=>x!==t.id); setGroupPerms(p=>({...p,[g.id]:next}))}}/>{t.name}</label>)}</div><button onClick={async()=>{await patchGroupTemplatePermissions(g.id,groupPerms[g.id]); setMsg('Group template permissions saved.')}}>Save Group Permissions</button></div>:null}
      </td></tr>)}
    </tbody></table>
  </section>
}
