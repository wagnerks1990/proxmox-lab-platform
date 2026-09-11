import React from 'react'

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
    return <main className='login-wrap'>
      <section className='login-card' role='alert'>
        <h1>LabGoblin needs to recover</h1>
        <p className='muted'>The interface encountered an unexpected error. No operation was reported as successful.</p>
        <div className='group'>
          <button onClick={() => this.setState({ failed: false })}>Try again</button>
          <button onClick={() => window.location.reload()}>Reload application</button>
        </div>
      </section>
    </main>
  }
}
