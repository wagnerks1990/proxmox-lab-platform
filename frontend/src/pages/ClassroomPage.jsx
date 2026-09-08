import { useEffect, useMemo, useState } from 'react'
import { listCurrentOrganizationMembers } from '../services/organizationApi'
import api from '../services/api'
import {
  addEnrollment,
  bulkAssignRun,
  changeLabRunState,
  createClass,
  createLab,
  createLabRun,
  listClasses,
  listEnrollments,
  listLabs,
  listLabRuns,
  listRunAssignments,
  removeEnrollment,
  revokeRunAssignment,
} from '../services/classroomApi'

const detail = error => typeof error?.response?.data?.detail === 'string' ? error.response.data.detail : JSON.stringify(error?.response?.data?.detail || 'Request failed')

export default function ClassroomPage({ setMessage }) {
  const [classes, setClasses] = useState([])
  const [labs, setLabs] = useState([])
  const [runs, setRuns] = useState([])
  const [pools, setPools] = useState([])
  const [members, setMembers] = useState([])
  const [selectedClass, setSelectedClass] = useState('')
  const [selectedRun, setSelectedRun] = useState('')
  const [enrollments, setEnrollments] = useState([])
  const [assignments, setAssignments] = useState([])
  const [classForm, setClassForm] = useState({ name: '', term: '' })
  const [labForm, setLabForm] = useState({ name: '', description: '', default_pool_id: '', student_can_power_off: false, terminal_enabled: true, console_enabled: true, rdp_enabled: false })
  const [runForm, setRunForm] = useState({ name: '', lab_id: '', starts_at: '', ends_at: '', max_vms_per_student: 1 })
  const [memberId, setMemberId] = useState('')

  const reload = async () => {
    const [classRows, labRows, runRows, poolResponse, memberRows] = await Promise.all([
      listClasses(), listLabs(), listLabRuns(), api.get('/pools'), listCurrentOrganizationMembers(),
    ])
    setClasses(classRows || []); setLabs(labRows || []); setRuns(runRows || [])
    setPools(poolResponse.data?.data || []); setMembers(memberRows || [])
  }
  useEffect(() => { reload().catch(error => setMessage({ type: 'error', text: detail(error) })) }, [])
  useEffect(() => { if (selectedClass) listEnrollments(selectedClass).then(setEnrollments).catch(() => setEnrollments([])) }, [selectedClass])
  useEffect(() => { if (selectedRun) listRunAssignments(selectedRun).then(setAssignments).catch(() => setAssignments([])) }, [selectedRun])

  const classLabs = useMemo(() => labs.filter(lab => String(lab.class_id) === String(selectedClass)), [labs, selectedClass])
  const selectedRunRow = runs.find(run => String(run.id) === String(selectedRun))
  const save = async (work, message) => { try { await work(); await reload(); setMessage({ type: 'success', text: message }) } catch (error) { setMessage({ type: 'error', text: detail(error) }) } }

  return <section>
    <h2>Classroom</h2>
    <p className='muted'>Create classes and lab blueprints, enroll students, open scheduled lab runs, and issue explicit VM assignments.</p>

    <div className='panel'><h3>1. Classes and roster</h3><div className='group'>
      <input className='input' placeholder='Class name' value={classForm.name} onChange={event => setClassForm({...classForm, name: event.target.value})} />
      <input className='input' placeholder='Term' value={classForm.term} onChange={event => setClassForm({...classForm, term: event.target.value})} />
      <button disabled={!classForm.name} onClick={() => save(async () => { await createClass(classForm); setClassForm({name:'',term:''}) }, 'Class created.')}>Create class</button>
      <select className='input' value={selectedClass} onChange={event => { setSelectedClass(event.target.value); setSelectedRun('') }}><option value=''>Select class…</option>{classes.map(row => <option key={row.id} value={row.id}>{row.name}{row.term ? ` — ${row.term}` : ''}</option>)}</select>
    </div>
    {selectedClass && <><div className='group' style={{marginTop:12}}><select className='input' value={memberId} onChange={event => setMemberId(event.target.value)}><option value=''>Select organization member…</option>{members.map(row => <option key={row.user_id} value={row.user_id}>{row.username} ({row.role})</option>)}</select><button disabled={!memberId} onClick={() => save(async () => { await addEnrollment(selectedClass, {user_id:Number(memberId), role:'student'}); setEnrollments(await listEnrollments(selectedClass)); setMemberId('') }, 'Student enrolled.')}>Enroll student</button></div>
      <table className='vm-table'><thead><tr><th>User ID</th><th>Role</th><th>Active</th><th>Action</th></tr></thead><tbody>{enrollments.map(row => <tr key={row.id}><td>{members.find(member => member.user_id === row.user_id)?.username || row.user_id}</td><td>{row.role || 'student'}</td><td>{String(row.is_active)}</td><td><button className='btn-danger' onClick={() => save(async () => { await removeEnrollment(selectedClass, row.user_id); setEnrollments(await listEnrollments(selectedClass)) }, 'Enrollment removed.')}>Remove</button></td></tr>)}</tbody></table></>}
    </div>

    <div className='panel'><h3>2. Lab blueprint</h3><div className='group'>
      <input className='input' placeholder='Lab name' value={labForm.name} onChange={event => setLabForm({...labForm,name:event.target.value})} />
      <select className='input' value={labForm.default_pool_id} onChange={event => setLabForm({...labForm,default_pool_id:event.target.value})}><option value=''>Select pool…</option>{pools.map(row => <option key={row.id} value={row.id}>{row.name}</option>)}</select>
      <label><input type='checkbox' checked={labForm.student_can_power_off} onChange={event => setLabForm({...labForm,student_can_power_off:event.target.checked})}/> student power off</label>
      <label><input type='checkbox' checked={labForm.terminal_enabled} onChange={event => setLabForm({...labForm,terminal_enabled:event.target.checked})}/> terminal</label>
      <label><input type='checkbox' checked={labForm.console_enabled} onChange={event => setLabForm({...labForm,console_enabled:event.target.checked})}/> console</label>
      <label><input type='checkbox' checked={labForm.rdp_enabled} onChange={event => setLabForm({...labForm,rdp_enabled:event.target.checked})}/> RDP</label>
      <button disabled={!selectedClass || !labForm.name || !labForm.default_pool_id} onClick={() => save(async () => { await createLab({...labForm,class_id:Number(selectedClass),default_pool_id:Number(labForm.default_pool_id)}); setLabForm({...labForm,name:'',description:''}) }, 'Lab blueprint created.')}>Create lab</button>
    </div>{selectedClass && <p className='muted'>Labs in selected class: {classLabs.map(row => row.name).join(', ') || 'none'}</p>}</div>

    <div className='panel'><h3>3. Scheduled run and assignments</h3><div className='group'>
      <select className='input' value={runForm.lab_id} onChange={event => setRunForm({...runForm,lab_id:event.target.value})}><option value=''>Select lab…</option>{classLabs.map(row => <option key={row.id} value={row.id}>{row.name}</option>)}</select>
      <input className='input' placeholder='Run name' value={runForm.name} onChange={event => setRunForm({...runForm,name:event.target.value})} />
      <label className='muted'>Starts <input className='input' type='datetime-local' value={runForm.starts_at} onChange={event => setRunForm({...runForm,starts_at:event.target.value})}/></label>
      <label className='muted'>Ends <input className='input' type='datetime-local' value={runForm.ends_at} onChange={event => setRunForm({...runForm,ends_at:event.target.value})}/></label>
      <label className='muted'>VMs/student <input className='input' type='number' min='1' max='10' value={runForm.max_vms_per_student} onChange={event => setRunForm({...runForm,max_vms_per_student:Number(event.target.value)})}/></label>
      <button disabled={!runForm.lab_id || !runForm.name} onClick={() => save(async () => { await createLabRun({...runForm,lab_id:Number(runForm.lab_id),starts_at:runForm.starts_at||null,ends_at:runForm.ends_at||null}); setRunForm({...runForm,name:''}) }, 'Lab run created.')}>Create run</button>
      <select className='input' value={selectedRun} onChange={event => setSelectedRun(event.target.value)}><option value=''>Select run…</option>{runs.filter(run => classLabs.some(lab => lab.id === run.lab_id)).map(row => <option key={row.id} value={row.id}>{row.name} — {row.state}</option>)}</select>
    </div>
    {selectedRunRow && <><div className='group' style={{marginTop:12}}><button onClick={() => save(async () => { await bulkAssignRun(selectedRun); setAssignments(await listRunAssignments(selectedRun)) }, 'Assignments created for the active roster.')}>Assign roster</button>{selectedRunRow.state === 'draft' && selectedRunRow.starts_at && <button onClick={() => save(() => changeLabRunState(selectedRun,'schedule'), 'Lab run scheduled; access will open inside its window.')}>Schedule</button>}{selectedRunRow.state === 'draft' && <button onClick={() => save(() => changeLabRunState(selectedRun,'activate'), 'Lab run activated.')}>Activate now</button>}{selectedRunRow.state === 'scheduled' && <button onClick={() => save(() => changeLabRunState(selectedRun,'activate'), 'Lab run activated.')}>Activate now</button>}{selectedRunRow.state === 'active' && <button className='btn-danger' onClick={() => save(() => changeLabRunState(selectedRun,'end'), 'Lab run ended and assignments expired.')}>End run</button>}</div>
      <p className='muted'>State: {selectedRunRow.state} | Currently open: {String(selectedRunRow.effective_open)} | Quota: {selectedRunRow.max_vms_per_student} VM(s) per student</p>
      <table className='vm-table'><thead><tr><th>Student</th><th>Slot</th><th>Template</th><th>Status</th><th>VM</th><th>Action</th></tr></thead><tbody>{assignments.map(row => <tr key={row.id}><td>{row.username || row.user_id}</td><td>{row.slot_index}</td><td>{row.template_name || row.template_id}</td><td>{row.status}</td><td>{row.student_vm_id || '-'}</td><td><button className='btn-danger' onClick={() => save(async () => { await revokeRunAssignment(selectedRun,row.id); setAssignments(await listRunAssignments(selectedRun)) }, 'Assignment revoked.')}>Revoke</button></td></tr>)}</tbody></table></>}
    </div>
  </section>
}
