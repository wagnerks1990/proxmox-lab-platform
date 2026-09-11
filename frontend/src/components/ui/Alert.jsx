export default function Alert({ tone = 'info', title, children, onDismiss, className = '' }) {
  const role = tone === 'error' ? 'alert' : 'status'
  return <div className={`ui-alert ui-alert--${tone} ${className}`.trim()} role={role} aria-live={tone === 'error' ? 'assertive' : 'polite'}>
    <div className='ui-alert__content'>
      {title ? <h3 className='ui-alert__title'>{title}</h3> : null}
      <div className='ui-alert__message'>{children}</div>
    </div>
    {onDismiss ? <button className='ui-alert__dismiss' type='button' onClick={onDismiss} aria-label='Dismiss message'>×</button> : null}
  </div>
}
