import { useEffect, useState } from 'react'
import { listUsers, createUser, patchUser, patchUserPassword, patchUserActivate, deleteUser, getUserActivity, revokeUserSessions } from '../services/adminUsersApi'

const empty = { username:'', email:'', display_name:'', role_id:1, password:'', is_active:true, force_password_change:true }

export default function UsersPage(){
  const [rows,setRows]=useState([])
  const [form,setForm]=useState(empty)
  const [editing,setEditing]=useState(null)
  const [msg,setMsg]=useState(null)
  const [activity,setActivity]=useState(null)
  const [resetUser,setResetUser]=useState(null)
  const [resetPassword,setResetPassword]=useState('')
  const [resetConfirmation,setResetConfirmation]=useState('')
  const [resetBusy,setResetBusy]=useState(false)
  const [resetError,setResetError]=useState('')

  const load = ()=> listUsers().then(setRows).catch(()=>setRows([]))
  useEffect(()=>{ load() },[])

  const save = async ()=> {
    try{
      if(editing){ await patchUser(editing, { username:form.username, email:form.email, display_name:form.display_name, role_id:Number(form.role_id), is_active:form.is_active, force_password_change:form.force_password_change }) }
      else { await createUser(form) }
      setForm(empty); setEditing(null); await load(); setMsg({type:'success',text:'User saved.'})
    } catch(e){ setMsg({type:'error',text:JSON.stringify(e?.response?.data?.detail || 'Save failed')}) }
  }

  const closeReset = () => {
    setResetUser(null); setResetPassword(''); setResetConfirmation(''); setResetError('')
  }

  const submitPasswordReset = async event => {
    event.preventDefault()
    setResetError('')
    if (resetPassword !== resetConfirmation) return setResetError('Passwords do not match.')
    setResetBusy(true)
    try {
      await patchUserPassword(resetUser.id, { password:resetPassword, force_password_change:true })
      setMsg({type:'success',text:`Password reset for ${resetUser.username}. Existing sessions were revoked.`})
      closeReset()
    } catch (error) {
      const detail = error?.response?.data?.detail
      setResetError(typeof detail === 'string' ? detail : 'Password reset failed.')
    } finally { setResetBusy(false) }
  }

  return <section>
    <h2>Users</h2>
    <p className='muted'>Platform account, role, password, and session management. Student VM access is assigned from Classroom.</p>
    {msg?<p className={`msg ${msg.type}`} role={msg.type==='error'?'alert':'status'} aria-live='polite'>{msg.text}</p>:null}
    <div className='panel'><h3>{editing?'Edit User':'Create User'}</h3><div className='group'>
      <input className='input' aria-label='Username' placeholder='Username' value={form.username} onChange={e=>setForm({...form,username:e.target.value})}/>
      <input className='input' aria-label='Email' placeholder='Email' value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/>
      <input className='input' aria-label='Display name' placeholder='Display name' value={form.display_name} onChange={e=>setForm({...form,display_name:e.target.value})}/>
      {!editing?<input className='input' aria-label='Initial password' placeholder='Password' type='password' autoComplete='new-password' value={form.password} onChange={e=>setForm({...form,password:e.target.value})}/>:null}
      <select className='input' aria-label='Platform role' value={form.role_id} onChange={e=>setForm({...form,role_id:Number(e.target.value)})}><option value='1'>Student</option><option value='2'>Teacher</option><option value='3'>Admin</option></select>
      <label><input type='checkbox' checked={form.is_active} onChange={e=>setForm({...form,is_active:e.target.checked})}/> active</label>
      <label><input type='checkbox' checked={form.force_password_change} onChange={e=>setForm({...form,force_password_change:e.target.checked})}/> force password change</label>
      <button onClick={save} disabled={!form.username || !form.email || (!editing && !form.password)}>Save</button>
    </div></div>
    {rows.length===0?<p className='muted'>No users found.</p>:null}
    <table className='vm-table'><thead><tr><th>Username</th><th>Email</th><th>Display</th><th>Role</th><th>Active</th><th>Force PW</th><th>Last Login</th><th>Actions</th></tr></thead><tbody>
      {rows.map(u=><tr key={u.id}><td>{u.username}</td><td>{u.email}</td><td>{u.display_name||'-'}</td><td>{u.role||u.role_id}</td><td>{String(u.is_active)}</td><td>{String(u.force_password_change)}</td><td>{u.last_login_at||'-'}</td><td><div className='group'>
        <button onClick={()=>{setEditing(u.id); setForm({...empty,...u, password:'', role_id:u.role_id})}}>Edit</button>
        <button onClick={()=>{setResetUser(u);setResetPassword('');setResetConfirmation('');setResetError('')}}>Reset Password</button>
        <button onClick={async()=>{try{const result=await revokeUserSessions(u.id);setMsg({type:'success',text:`${result.sessions_revoked} session(s) revoked.`})}catch(error){setMsg({type:'error',text:error?.response?.data?.detail||'Session revocation failed.'})}}}>Revoke Sessions</button>
        <button onClick={async()=>{await patchUserActivate(u.id,!u.is_active); await load()}}>{u.is_active?'Deactivate':'Activate'}</button>
        <button onClick={async()=>{setActivity(await getUserActivity(u.id))}}>Activity</button>
        <button className='btn-danger' onClick={async()=>{if(!confirm('Delete user? If dependencies exist, backend may deactivate instead.')) return; const r=await deleteUser(u.id); setMsg({type:'success',text:r.message||'Delete/deactivate completed.'}); await load()}}>Delete/Deactivate</button>
      </div></td></tr>)}
    </tbody></table>
    {activity?<div className='panel'><h3>User Activity</h3><p className='muted'>VMs: {activity.vm_count} | Sessions: {activity.session_count} | Audit logs: {activity.audit_log_count} | Last login: {activity.last_login_at||'-'}</p></div>:null}
    {resetUser ? <div className='modal-backdrop' role='presentation' onMouseDown={event=>{if(event.target===event.currentTarget&&!resetBusy)closeReset()}}>
      <form className='panel modal-dialog' role='dialog' aria-modal='true' aria-labelledby='reset-password-title' onSubmit={submitPasswordReset} onKeyDown={event=>{if(event.key==='Escape'&&!resetBusy)closeReset()}}>
        <h3 id='reset-password-title'>Reset password for {resetUser.username}</h3>
        <p className='muted' id='reset-password-help'>The user will be required to change this password at next sign-in.</p>
        {resetError?<p className='msg error' role='alert'>{resetError}</p>:null}
        <label htmlFor='reset-password'>New password</label>
        <input id='reset-password' className='input' type='password' autoComplete='new-password' aria-describedby='reset-password-help' value={resetPassword} onChange={event=>setResetPassword(event.target.value)} autoFocus/>
        <label htmlFor='reset-password-confirmation'>Confirm new password</label>
        <input id='reset-password-confirmation' className='input' type='password' autoComplete='new-password' value={resetConfirmation} onChange={event=>setResetConfirmation(event.target.value)}/>
        <div className='group'><button type='submit' disabled={resetBusy||!resetPassword||!resetConfirmation}>{resetBusy?'Resetting…':'Reset password'}</button><button type='button' disabled={resetBusy} onClick={closeReset}>Cancel</button></div>
      </form>
    </div> : null}
  </section>
}
