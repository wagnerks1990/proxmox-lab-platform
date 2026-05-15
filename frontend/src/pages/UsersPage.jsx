import { useEffect, useState } from 'react'
import api from '../services/api'

export default function UsersPage({ setMessage }) {
  const [users,setUsers]=useState([]); const [groups,setGroups]=useState([]); const [groupName,setGroupName]=useState('')
  const load=()=>{api.get('/admin/users').then(r=>setUsers(r.data)); api.get('/admin/groups').then(r=>setGroups(r.data))}
  useEffect(()=>{load()},[])
  const createGroup=async()=>{try{await api.post('/admin/groups',{name:groupName});setGroupName('');load()}catch(e){setMessage({type:'error',text:'Group create failed'})}}
  return <section className='grid-2'><div className='panel'><h2>Users</h2><table className='table2'><thead><tr><th>User</th><th>Role</th><th>VM Count</th></tr></thead><tbody>{users.map(u=><tr key={u.id}><td>{u.username}</td><td>{u.role}</td><td>{u.vm_count}</td></tr>)}</tbody></table></div><div className='panel'><h2>Groups</h2><div className='group'><input className='input' value={groupName} onChange={e=>setGroupName(e.target.value)} placeholder='New group'/><button className='btn' onClick={createGroup}>Create</button></div><table className='table2'><thead><tr><th>Name</th><th>Description</th></tr></thead><tbody>{groups.map(g=><tr key={g.id}><td>{g.name}</td><td>{g.description||'-'}</td></tr>)}</tbody></table></div></section>
}
