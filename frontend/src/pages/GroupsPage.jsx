import { useEffect, useState } from 'react'
import { listGroups, createGroup, patchGroup, deleteGroup, listGroupMembers, addGroupMember, removeGroupMember } from '../services/adminGroupsApi'
import { listCurrentOrganizationMembers } from '../services/organizationApi'

const empty = { name:'', description:'', enabled:true }

export default function GroupsPage(){
  const [rows,setRows]=useState([])
  const [users,setUsers]=useState([])
  const [form,setForm]=useState(empty)
  const [editing,setEditing]=useState(null)
  const [members,setMembers]=useState({})
  const [msg,setMsg]=useState('')

  const load = ()=> listGroups().then(setRows).catch(()=>setRows([]))
  useEffect(()=>{ load(); listCurrentOrganizationMembers().then(rows=>setUsers(rows.map(row=>({id:row.user_id,...row})))).catch(()=>setUsers([])) },[])

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
    <p className='muted'>Manage tenant groups and memberships. Classroom VM access is controlled by lab assignments.</p>
    {msg?<p className='muted'>{msg}</p>:null}
    <div className='panel'><h3>{editing?'Edit Group':'Create Group'}</h3><div className='group'>
      <input className='input' placeholder='Name' value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/>
      <input className='input' placeholder='Description' value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/>
      <label><input type='checkbox' checked={form.enabled} onChange={e=>setForm({...form,enabled:e.target.checked})}/> enabled</label>
      <button onClick={save} disabled={!form.name}>Save</button>
    </div></div>
    {rows.length===0?<p className='muted'>No groups/classes configured yet.</p>:null}
    <table className='vm-table'><thead><tr><th>Name</th><th>Enabled</th><th>Members</th><th>Actions</th></tr></thead><tbody>
      {rows.map(g=><tr key={g.id}><td>{g.name}</td><td>{String(g.enabled)}</td><td>{g.member_count}</td><td><div className='group'>
        <button onClick={()=>{setEditing(g.id); setForm({name:g.name,description:g.description||'',enabled:g.enabled})}}>Edit</button>
        <button onClick={async()=>{await loadMembers(g.id)}}>Members</button>
        <button className='btn-danger' onClick={async()=>{if(!confirm('Delete group? This removes memberships/permissions but not users/VMs.')) return; await deleteGroup(g.id); await load()}}>Delete</button>
      </div>
      {Array.isArray(members[g.id])?<div className='panel'><h4>Members</h4><div className='group'>{members[g.id].map(m=><span key={m.user_id}>{m.username||m.user_id} <button onClick={async()=>{await removeMember(g.id,m.user_id)}}>x</button></span>)}</div><select className='input' onChange={async e=>{const uid=Number(e.target.value); await addMember(g.id,uid)}}><option value=''>Add user…</option>{users.map(u=><option key={u.id} value={u.id}>{u.username}</option>)}</select></div>:null}
      </td></tr>)}
    </tbody></table>
  </section>
}
