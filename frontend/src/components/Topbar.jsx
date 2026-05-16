export default function Topbar({ user, onLogout }) {
  return <header className='topbar'><div>Classroom VDI Portal</div><div className='top-right'>{user?.username} ({user?.role}) <button className='btn ghost' onClick={onLogout}>Logout</button></div></header>
}
