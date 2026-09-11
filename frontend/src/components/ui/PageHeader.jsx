export default function PageHeader({ title, description, eyebrow, actions, children, className = '' }) {
  return <header className={`ui-page-header ${className}`.trim()}>
    <div className='ui-page-header__copy'>
      {eyebrow ? <div className='muted'>{eyebrow}</div> : null}
      <h1 className='ui-page-header__title'>{title}</h1>
      {description ? <p className='ui-page-header__description'>{description}</p> : null}
      {children}
    </div>
    {actions ? <div className='ui-page-header__actions'>{actions}</div> : null}
  </header>
}
