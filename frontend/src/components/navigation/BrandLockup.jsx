import { Link } from 'react-router-dom'

export default function BrandLockup({ compact = false, onNavigate }) {
  return <Link className={`brand-lockup${compact ? ' brand-lockup-compact' : ''}`} to='/' onClick={onNavigate} aria-label='LabGoblin home'>
    <img src='/brand/labgoblin-icon.svg' alt='' className='brand-mark'/>
    <span className='brand-copy'>
      <span className='brand-wordmark'>Lab<span>Goblin</span></span>
      <span className='brand-subtitle'>Virtual Lab Management</span>
    </span>
  </Link>
}
