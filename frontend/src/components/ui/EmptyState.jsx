export default function EmptyState({ title, description, action, children, className = '' }) {
  return <section className={`ui-empty-state ${className}`.trim()}>
    <div className='ui-empty-state__content'>
      <h3 className='ui-empty-state__title'>{title}</h3>
      {description ? <p className='ui-empty-state__description'>{description}</p> : null}
      {children}
      {action ? <div className='ui-cluster ui-empty-state__actions'>{action}</div> : null}
    </div>
  </section>
}
