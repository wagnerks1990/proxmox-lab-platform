import { Link, useLocation } from 'react-router-dom'
import { isNavigationItemActive, mobileNavigation } from '../../navigation/appNavigation'
import NavIcon from './NavIcon'

export default function MobileBottomNav({ access, onMore }) {
  const { pathname } = useLocation()
  const items = mobileNavigation(access)
  return <nav className='mobile-bottom-nav' aria-label='Quick navigation'>
    {items.map(item => {
      const active = isNavigationItemActive(item, pathname)
      return <Link className={`mobile-bottom-link${active ? ' mobile-bottom-link-active' : ''}`} to={item.to} key={item.id} aria-current={active ? 'page' : undefined}>
        <NavIcon name={item.icon}/><span>{item.shortLabel}</span>
      </Link>
    })}
    <button className='mobile-bottom-link' type='button' onClick={onMore} aria-label='Open more navigation'>
      <NavIcon name='menu'/><span>More</span>
    </button>
  </nav>
}
