import { useId } from 'react'

export default function Tabs({ tabs = [], activeId, onChange, label = 'Sections', className = '' }) {
  const generatedId = useId().replaceAll(':', '')
  const selected = tabs.find(tab => tab.id === activeId) || tabs.find(tab => !tab.disabled) || tabs[0]
  if (!selected) return null

  const moveFocus = (event, currentId) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
    event.preventDefault()
    const enabled = tabs.filter(tab => !tab.disabled)
    const currentIndex = enabled.findIndex(tab => tab.id === currentId)
    const nextIndex = event.key === 'Home' ? 0
      : event.key === 'End' ? enabled.length - 1
        : (currentIndex + (event.key === 'ArrowRight' ? 1 : -1) + enabled.length) % enabled.length
    const next = enabled[nextIndex]
    onChange?.(next.id)
    event.currentTarget.parentElement?.querySelector(`#${CSS.escape(`${generatedId}-tab-${next.id}`)}`)?.focus()
  }

  return <div className={`ui-tabs ${className}`.trim()}>
    <div className='ui-tabs__list' role='tablist' aria-label={label}>
      {tabs.map(tab => <button
        key={tab.id}
        id={`${generatedId}-tab-${tab.id}`}
        className='ui-tabs__tab'
        type='button'
        role='tab'
        aria-selected={tab.id === selected.id}
        aria-controls={`${generatedId}-panel-${tab.id}`}
        disabled={tab.disabled}
        tabIndex={tab.id === selected.id ? 0 : -1}
        onClick={() => onChange?.(tab.id)}
        onKeyDown={event => moveFocus(event, tab.id)}
      >{tab.label}</button>)}
    </div>
    <div id={`${generatedId}-panel-${selected.id}`} className='ui-tabs__panel' role='tabpanel' aria-labelledby={`${generatedId}-tab-${selected.id}`}>
      {selected.content}
    </div>
  </div>
}
