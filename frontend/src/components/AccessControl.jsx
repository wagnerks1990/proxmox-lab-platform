import { createContext, useContext } from 'react'
import { Link } from 'react-router-dom'

export const AccessContext = createContext({ platformAdmin: false, tenantInstructor: false, tenantAdmin: false })

export function RequireCapability({ capability, children }) {
  const access = useContext(AccessContext)
  return access[capability] ? children : <ForbiddenPage />
}

export function ForbiddenPage() {
  return <section className='panel' role='alert'>
    <h2>Access denied</h2>
    <p className='muted'>Your role in the selected organization does not allow access to this page.</p>
    <Link to='/'>Return to dashboard</Link>
  </section>
}
