import React from 'react'
import Button from './ui/Button'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { failed: false }
  }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    if (!this.state.failed) return this.props.children
    return <main className='auth-shell'>
      <section className='auth-card ui-stack' role='alert' aria-labelledby='recovery-title'>
        <h1 id='recovery-title'>LabGoblin needs to recover</h1>
        <p className='muted'>The interface encountered an unexpected error. No operation was reported as successful.</p>
        <div className='ui-cluster'>
          <Button onClick={() => this.setState({ failed: false })}>Try again</Button>
          <Button variant='secondary' onClick={() => window.location.reload()}>Reload application</Button>
        </div>
      </section>
    </main>
  }
}
