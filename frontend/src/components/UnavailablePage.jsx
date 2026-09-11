import Button from './ui/Button'

export default function UnavailablePage({ message, onRetry, busy }) {
  return <main className='auth-shell'>
    <section className='auth-card ui-stack' role='alert' aria-labelledby='unavailable-title'>
      <h1 id='unavailable-title'>LabGoblin is unavailable</h1>
      <p className='muted'>{message}</p>
      <Button block busy={busy} onClick={onRetry}>{busy ? 'Checking connection…' : 'Try again'}</Button>
    </section>
  </main>
}
