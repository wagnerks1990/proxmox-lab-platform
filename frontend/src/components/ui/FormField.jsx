import { cloneElement, isValidElement, useId } from 'react'

export default function FormField({ label, hint, error, required = false, children, className = '', id: suppliedId }) {
  const generatedId = useId()
  const childId = isValidElement(children) ? children.props.id : undefined
  const id = suppliedId || childId || `field-${generatedId.replaceAll(':', '')}`
  const hintId = hint ? `${id}-hint` : undefined
  const errorId = error ? `${id}-error` : undefined
  const childDescription = isValidElement(children) ? children.props['aria-describedby'] : undefined
  const describedBy = [childDescription, hintId, errorId].filter(Boolean).join(' ') || undefined
  const control = isValidElement(children)
    ? cloneElement(children, {
      id: children.props.id || id,
      required: children.props.required ?? required,
      'aria-describedby': describedBy,
      'aria-invalid': children.props['aria-invalid'] ?? (error ? true : undefined),
    })
    : children

  return <div className={`ui-field ${className}`.trim()}>
    <label className='ui-field__label' htmlFor={id}>
      {label}{required ? <span className='ui-field__required' aria-hidden='true'> *</span> : null}
    </label>
    {control}
    {hint ? <p className='ui-field__hint' id={hintId}>{hint}</p> : null}
    {error ? <p className='ui-field__error' id={errorId} role='alert'>{error}</p> : null}
  </div>
}
