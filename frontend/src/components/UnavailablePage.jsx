export default function UnavailablePage({ message, onRetry, busy }) {
  return <main className='login-wrap'>
    <section className='login-card' role='alert'>
      <h1>LabGoblin is unavailable</h1>
      <p className='muted'>{message}</p>
      <button onClick={onRetry} disabled={busy} style={{width:'100%'}}>{busy ? 'Checking…' : 'Try again'}</button>
    </section>
  </main>
}
