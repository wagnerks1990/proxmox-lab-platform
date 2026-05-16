import { useNavigate } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import Topbar from '../components/Topbar'

export default function AppLayout({ children, setUser, user }) {
  const nav = useNavigate()
  const logout = () => { localStorage.removeItem('token'); setUser(false); nav('/') }
  return <div className='app2'>
    <Sidebar user={user} />
    <div className='main2'>
      <Topbar user={user} onLogout={logout} />
      <div className='page2'>{children}</div>
    </div>
  </div>
}
