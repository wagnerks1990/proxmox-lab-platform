import { NavLink, useLocation } from 'react-router-dom'
import { isNavigationItemActive, visibleNavigation } from '../../navigation/appNavigation'
import NavIcon from './NavIcon'

export default function NavigationLinks({ access, compact = false, onNavigate }) {
  const { pathname } = useLocation()
  return <nav className={compact ? 'sidebar-navigation sidebar-navigation-compact' : 'sidebar-navigation'} aria-label='Primary navigation'>
    {visibleNavigation(access).map(group => <section className='nav-group' key={group.id} aria-labelledby={`nav-group-${group.id}`}>
      <h2 className='nav-group-label' id={`nav-group-${group.id}`}>{group.label}</h2>
      <div className='nav-group-links'>
        {group.items.map(item => {
          const active = isNavigationItemActive(item, pathname)
          return <NavLink
            className={`nav-link${active ? ' nav-link-active' : ''}`}
            to={item.to}
            key={item.id}
            aria-current={active ? 'page' : undefined}
            onClick={onNavigate}
            title={compact ? item.label : undefined}
          >
            <NavIcon name={item.icon}/><span className='nav-link-label'>{item.label}</span>
          </NavLink>
        })}
      </div>
    </section>)}
  </nav>
}
