import { forwardRef } from 'react'

const Button = forwardRef(function Button({
  variant = 'primary',
  size = 'default',
  block = false,
  busy = false,
  disabled = false,
  children,
  className = '',
  type = 'button',
  ...props
}, ref) {
  const classes = [
    'ui-button',
    `ui-button--${variant}`,
    size !== 'default' ? `ui-button--${size}` : '',
    block ? 'ui-button--block' : '',
    className,
  ].filter(Boolean).join(' ')

  return <button ref={ref} type={type} className={classes} disabled={disabled || busy} aria-busy={busy || undefined} {...props}>
    {busy ? <span className='ui-button__spinner' aria-hidden='true' /> : null}
    {children}
  </button>
})

export default Button
