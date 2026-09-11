import BrandLockup from './BrandLockup'
import NavIcon from './NavIcon'
import NavigationLinks from './NavigationLinks'

export default function AppSidebar({ access, collapsed, onToggle }) {
  return <aside className={`sidebar desktop-sidebar${collapsed ? ' sidebar-collapsed' : ''}`} aria-label='Application sidebar'>
    <div className='sidebar-header'>
      <BrandLockup compact={collapsed}/>
      <button className='sidebar-collapse-button icon-button' type='button' onClick={onToggle} aria-expanded={!collapsed} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
        <NavIcon name={collapsed ? 'expand' : 'collapse'}/>
      </button>
    </div>
    <NavigationLinks access={access} compact={collapsed}/>
    <div className='sidebar-brand-footer'>
      <span className='brand-footer'>Real Skills. Virtual Machines.</span>
    </div>
  </aside>
}
