export default function Card({ as: Element = 'section', variant = 'default', interactive = false, className = '', children, ...props }) {
  const classes = ['ui-card', variant !== 'default' ? `ui-card--${variant}` : '', interactive ? 'ui-card--interactive' : '', className].filter(Boolean).join(' ')
  return <Element className={classes} {...props}>{children}</Element>
}

export function CardHeader({ title, description, actions, headingLevel = 2, className = '' }) {
  const Heading = `h${headingLevel}`
  return <header className={`ui-card__header ${className}`.trim()}>
    <div>
      <Heading className='ui-card__title'>{title}</Heading>
      {description ? <p className='ui-card__description'>{description}</p> : null}
    </div>
    {actions ? <div className='ui-cluster'>{actions}</div> : null}
  </header>
}
