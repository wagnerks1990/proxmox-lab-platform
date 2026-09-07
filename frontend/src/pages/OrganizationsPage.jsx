import { useEffect, useState } from 'react'
import { listUsers } from '../services/adminUsersApi'
import {
  createOrganization,
  deactivateOrganizationMember,
  listAdminOrganizations,
  listOrganizationMembers,
  patchOrganization,
  putOrganizationMember,
} from '../services/adminOrganizationsApi'

const emptyOrganization = { name: '', slug: '', enabled: true }

export default function OrganizationsPage() {
  const [organizations, setOrganizations] = useState([])
  const [users, setUsers] = useState([])
  const [form, setForm] = useState(emptyOrganization)
  const [selectedId, setSelectedId] = useState(null)
  const [members, setMembers] = useState([])
  const [memberForm, setMemberForm] = useState({ user_id: '', role: 'student' })
  const [message, setMessage] = useState('')

  const loadOrganizations = async () => setOrganizations(await listAdminOrganizations())
  const loadMembers = async (id) => {
    setSelectedId(id)
    setMembers(await listOrganizationMembers(id))
  }

  useEffect(() => {
    Promise.all([listAdminOrganizations(), listUsers()]).then(([organizationRows, userRows]) => {
      setOrganizations(organizationRows)
      setUsers(userRows)
    }).catch(error => setMessage(error?.response?.data?.detail || 'Unable to load organization administration.'))
  }, [])

  const create = async () => {
    try {
      await createOrganization(form)
      setForm(emptyOrganization)
      await loadOrganizations()
      setMessage('Organization created. You were added as its first owner.')
    } catch (error) {
      setMessage(error?.response?.data?.detail || 'Organization creation failed.')
    }
  }

  const saveMember = async () => {
    if (!selectedId || !memberForm.user_id) return
    try {
      await putOrganizationMember(selectedId, Number(memberForm.user_id), { role: memberForm.role, is_active: true })
      await loadMembers(selectedId)
      await loadOrganizations()
      setMessage('Organization membership saved.')
    } catch (error) {
      setMessage(error?.response?.data?.detail || 'Membership update failed.')
    }
  }

  return <section>
    <h2>Organizations</h2>
    <p className='muted'>Platform administration for tenant boundaries and membership roles. The API prevents removing the last active owner.</p>
    {message ? <p className='msg'>{typeof message === 'string' ? message : JSON.stringify(message)}</p> : null}

    <div className='panel'>
      <h3>Create organization</h3>
      <div className='group'>
        <input className='input' placeholder='Organization name' value={form.name} onChange={event => setForm({...form, name: event.target.value})} />
        <input className='input' placeholder='slug-like-this' value={form.slug} onChange={event => setForm({...form, slug: event.target.value.toLowerCase()})} />
        <label><input type='checkbox' checked={form.enabled} onChange={event => setForm({...form, enabled: event.target.checked})} /> enabled</label>
        <button disabled={!form.name || !form.slug} onClick={create}>Create</button>
      </div>
    </div>

    <table className='vm-table'>
      <thead><tr><th>Name</th><th>Slug</th><th>Enabled</th><th>Members</th><th>Actions</th></tr></thead>
      <tbody>{organizations.map(organization => <tr key={organization.id}>
        <td>{organization.name}</td><td>{organization.slug}</td><td>{String(organization.enabled)}</td><td>{organization.member_count}</td>
        <td><div className='group'>
          <button onClick={() => loadMembers(organization.id)}>Members</button>
          <button onClick={async () => { await patchOrganization(organization.id, { enabled: !organization.enabled }); await loadOrganizations() }}>{organization.enabled ? 'Disable' : 'Enable'}</button>
        </div></td>
      </tr>)}</tbody>
    </table>

    {selectedId ? <div className='panel'>
      <h3>Members: {organizations.find(row => row.id === selectedId)?.name || selectedId}</h3>
      <table className='vm-table'><thead><tr><th>User</th><th>Role</th><th>Active</th><th>Actions</th></tr></thead><tbody>
        {members.map(member => <tr key={member.user_id}><td>{member.username || member.user_id}</td><td>{member.role}</td><td>{String(member.is_active)}</td><td><div className='group'>
          <select value={member.role} onChange={async event => { await putOrganizationMember(selectedId, member.user_id, { role: event.target.value, is_active: member.is_active }); await loadMembers(selectedId) }}>
            <option value='student'>Student</option><option value='instructor'>Instructor</option><option value='admin'>Admin</option><option value='owner'>Owner</option>
          </select>
          {member.is_active ? <button className='btn-danger' onClick={async () => { try { await deactivateOrganizationMember(selectedId, member.user_id); await loadMembers(selectedId); await loadOrganizations() } catch (error) { setMessage(error?.response?.data?.detail || 'Deactivation failed.') } }}>Deactivate</button> : <button onClick={async () => { await putOrganizationMember(selectedId, member.user_id, { role: member.role, is_active: true }); await loadMembers(selectedId) }}>Reactivate</button>}
        </div></td></tr>)}
      </tbody></table>
      <div className='group' style={{marginTop: 12}}>
        <select className='input' value={memberForm.user_id} onChange={event => setMemberForm({...memberForm, user_id: event.target.value})}>
          <option value=''>Select user…</option>{users.map(user => <option key={user.id} value={user.id}>{user.username} ({user.email})</option>)}
        </select>
        <select className='input' value={memberForm.role} onChange={event => setMemberForm({...memberForm, role: event.target.value})}>
          <option value='student'>Student</option><option value='instructor'>Instructor</option><option value='admin'>Admin</option><option value='owner'>Owner</option>
        </select>
        <button disabled={!memberForm.user_id} onClick={saveMember}>Add or update member</button>
      </div>
    </div> : null}
  </section>
}
