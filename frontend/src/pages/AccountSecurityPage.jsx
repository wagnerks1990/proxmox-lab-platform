import { useEffect, useState } from 'react'
import { changePassword, listSessions, revokeSession } from '../services/authApi'

export default function AccountSecurityPage({ forceChange = false, onChanged, setMessage }) {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [sessions, setSessions] = useState([])
  const [error, setError] = useState('')
  const load = () => listSessions().then(setSessions).catch(() => setSessions([]))
  useEffect(() => { load() }, [])

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    if (newPassword !== confirmPassword) return setError('New passwords do not match.')
    try {
      await changePassword({ current_password: currentPassword, new_password: newPassword })
      setCurrentPassword(''); setNewPassword(''); setConfirmPassword('')
      setMessage?.({ type: 'success', text: 'Password changed and other sessions revoked.' })
      await load()
      await onChanged?.()
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || 'Password change failed.')
    }
  }

  return <section>
    <h2>{forceChange ? 'Password change required' : 'Account Security'}</h2>
    <p className='muted'>{forceChange ? 'Set a private password before continuing.' : 'Change your password and review signed-in sessions.'}</p>
    <form className='panel' onSubmit={submit}>
      <h3>Change Password</h3>
      {error ? <p className='error'>{error}</p> : null}
      <div className='group'>
        <input className='input' type='password' autoComplete='current-password' placeholder='Current password' value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} />
        <input className='input' type='password' autoComplete='new-password' placeholder='New password' value={newPassword} onChange={event => setNewPassword(event.target.value)} />
        <input className='input' type='password' autoComplete='new-password' placeholder='Confirm new password' value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} />
        <button disabled={!currentPassword || !newPassword || !confirmPassword}>Change password</button>
      </div>
      <p className='muted'>Use at least 12 characters with upper- and lower-case letters, a number, and a symbol.</p>
    </form>
    {!forceChange && <div className='panel'>
      <h3>Active Sessions</h3>
      {sessions.length === 0 ? <p className='muted'>No active sessions found.</p> : <table className='vm-table'><thead><tr><th>Device</th><th>IP</th><th>Created</th><th>Expires</th><th>Action</th></tr></thead><tbody>
        {sessions.map(session => <tr key={session.id}><td>{session.current ? 'Current session' : (session.user_agent || 'Unknown device')}</td><td>{session.client_ip || '-'}</td><td>{session.created_at || '-'}</td><td>{session.expires_at || '-'}</td><td><button className='btn-danger' onClick={async () => { await revokeSession(session.id); if (session.current) { window.location.reload() } else { await load() } }}>Revoke</button></td></tr>)}
      </tbody></table>}
    </div>}
  </section>
}
