import { useEffect, useState } from 'react'
import { listUsers, createUser, patchUser, patchUserPassword, patchUserActivate, deleteUser, getUserActivity, revokeUserSessions } from '../services/adminUsersApi'

const empty = { username:'', email:'', display_name:'', role:'Student', password:'', is_active:true, force_password_change:true }

export default function UsersPage(){
  const [rows,setRows]=useState([])
  const [form,setForm]=useState(empty)
  const [editing,setEditing]=useState(null)
  const [msg,setMsg]=useState('')
  const [activity,setActivity]=useState(null)

  const load = ()=> listUsers().then(setRows).catch(()=>setRows([]))
  useEffect(()=>{ load() },[])

  const save = async ()=> {
    try{
      if(editing){ await patchUser(editing, { username:form.username, email:form.email, display_name:form.display_name, is_active:form.is_active, force_password_change:form.force_password_change }) }
      else { await createUser(form) }
      setForm(empty); setEditing(null); await load(); setMsg('User saved.')
    } catch(e){ setMsg(JSON.stringify(e?.response?.data?.detail || 'Save failed')) }
  }

  return <section>
    <h2>Users</h2>
    <p className='muted'>Platform account, role, password, and session management. Student VM access is assigned from Classroom.</p>
    {msg?<p className='muted'>{msg}</p>:null}
    <div className='panel'><h3>{editing?'Edit User':'Create User'}</h3><div className='group'>
      <input className='input' placeholder='Username' value={form.username} onChange={e=>setForm({...form,username:e.target.value})}/>
      <input className='input' placeholder='Email' value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/>
      <input className='input' placeholder='Display name' value={form.display_name} onChange={e=>setForm({...form,display_name:e.target.value})}/>
      {!editing?<input className='input' placeholder='Password' type='password' value={form.password} onChange={e=>setForm({...form,password:e.target.value})}/>:null}
      <select className='input' value={form.role} onChange={e=>setForm({...form,role:e.target.value})}><option>Student</option><option>Teacher</option><option>Admin</option></select>
      <label><input type='checkbox' checked={form.is_active} onChange={e=>setForm({...form,is_active:e.target.checked})}/> active</label>
      <label><input type='checkbox' checked={form.force_password_change} onChange={e=>setForm({...form,force_password_change:e.target.checked})}/> force password change</label>
      <button onClick={save} disabled={!form.username || !form.email || (!editing && !form.password)}>Save</button>
    </div></div>
    {rows.length===0?<p className='muted'>No users found.</p>:null}
    <table className='vm-table'><thead><tr><th>Username</th><th>Email</th><th>Display</th><th>Role</th><th>Active</th><th>Force PW</th><th>Last Login</th><th>Actions</th></tr></thead><tbody>
      {rows.map(u=><tr key={u.id}><td>{u.username}</td><td>{u.email}</td><td>{u.display_name||'-'}</td><td>{u.role||u.role_id}</td><td>{String(u.is_active)}</td><td>{String(u.force_password_change)}</td><td>{u.last_login_at||'-'}</td><td><div className='group'>
        <button onClick={()=>{setEditing(u.id); setForm({...empty,...u, password:'', role:u.role||'Student'})}}>Edit</button>
        <button onClick={async()=>{const np=prompt('New password'); if(!np) return; await patchUserPassword(u.id,{password:np, force_password_change:true}); setMsg('Password reset.')}}>Reset Password</button>
        <button onClick={async()=>{const result=await revokeUserSessions(u.id); setMsg(`${result.sessions_revoked} session(s) revoked.`)}}>Revoke Sessions</button>
        <button onClick={async()=>{await patchUserActivate(u.id,!u.is_active); await load()}}>{u.is_active?'Deactivate':'Activate'}</button>
        <button onClick={async()=>{setActivity(await getUserActivity(u.id))}}>Activity</button>
        <button className='btn-danger' onClick={async()=>{if(!confirm('Delete user? If dependencies exist, backend may deactivate instead.')) return; const r=await deleteUser(u.id); setMsg(r.message||'Delete/deactivate completed.'); await load()}}>Delete/Deactivate</button>
      </div></td></tr>)}
    </tbody></table>
    {activity?<div className='panel'><h3>User Activity</h3><p className='muted'>VMs: {activity.vm_count} | Sessions: {activity.session_count} | Audit logs: {activity.audit_log_count} | Last login: {activity.last_login_at||'-'}</p></div>:null}
  </section>
}
