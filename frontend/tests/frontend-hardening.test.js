import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import test from 'node:test'

import { deriveCapabilities } from '../src/auth/access.js'
import { AUTH_UNAVAILABLE_MESSAGE, classifyAuthFailure } from '../src/auth/authState.js'
import { normalizeMessage } from '../src/components/message.js'
import {
  appendOperationalEvent,
  getOperationalSnapshot,
  subscribeOperational,
  updateOperational,
  updateOperationalDebug,
} from '../src/state/operationalStore.js'

test('operational store publishes immutable snapshots for every update', () => {
  const snapshots = []
  const unsubscribe = subscribeOperational(() => snapshots.push(getOperationalSnapshot()))
  const before = getOperationalSnapshot()

  updateOperational({ status: 'connected', connected: true })
  const afterStatus = getOperationalSnapshot()
  updateOperationalDebug({ readyState: 1 })
  const afterDebug = getOperationalSnapshot()
  appendOperationalEvent('event-one')
  const afterEvent = getOperationalSnapshot()
  unsubscribe()

  assert.notStrictEqual(afterStatus, before)
  assert.notStrictEqual(afterDebug, afterStatus)
  assert.notStrictEqual(afterDebug.debug, afterStatus.debug)
  assert.notStrictEqual(afterEvent, afterDebug)
  assert.deepEqual(snapshots, [afterStatus, afterDebug, afterEvent])
  assert.equal(afterEvent.events[0], 'event-one')
})

test('message normalization supports legacy strings and structured messages', () => {
  assert.deepEqual(normalizeMessage('Update requested'), { type: 'success', text: 'Update requested' })
  assert.deepEqual(normalizeMessage({ type: 'error', text: 'Update failed' }), { type: 'error', text: 'Update failed' })
  assert.deepEqual(normalizeMessage({ type: 'error', detail: { field: 'branch', issue: 'invalid' } }), {
    type: 'error',
    text: '{"field":"branch","issue":"invalid"}',
  })
  assert.equal(normalizeMessage(null), null)
})

test('system update feedback supplies explicit success and error message types', () => {
  const source = readFileSync(new URL('../src/pages/SystemUpdatePage.jsx', import.meta.url), 'utf8')
  assert.match(source, /setMessage\(\{ type: 'success', text:/)
  assert.match(source, /setMessage\(\{ type: 'error', text:/)
  assert.doesNotMatch(source, /setMessage\(e\?\./)
})

test('logout failures keep the authenticated UI active and surface an error', () => {
  const source = readFileSync(new URL('../src/layouts/AppLayout.jsx', import.meta.url), 'utf8')
  const successBlock = source.slice(source.indexOf('try {'), source.indexOf('} catch (error)'))
  const failureBlock = source.slice(source.indexOf('} catch (error)'), source.indexOf('} finally'))

  assert.match(successBlock, /setUser\(false\)/)
  assert.doesNotMatch(failureBlock, /setUser\(false\)/)
  assert.match(failureBlock, /setLogoutError/)
})

test('terminal preserves failure state when the socket closes and observes container resizing', () => {
  const source = readFileSync(new URL('../src/pages/TerminalPage.jsx', import.meta.url), 'utf8')
  assert.match(source, /current === 'failed' \|\| event\.code !== 1000 \? 'failed' : 'closed'/)
  assert.match(source, /new ResizeObserver\(fitTerminal\)/)
  assert.doesNotMatch(source, /JSON\.stringify\([^\n]*cols|type:\s*['"]resize['"]/)
})

test('authentication failures distinguish an invalid session from an unavailable API', () => {
  assert.deepEqual(classifyAuthFailure({ response: { status: 401 } }), { user: false, error: null })
  assert.deepEqual(classifyAuthFailure({ response: { status: 503 } }), { user: null, error: AUTH_UNAVAILABLE_MESSAGE })
  assert.deepEqual(classifyAuthFailure(new TypeError('Network error')), { user: null, error: AUTH_UNAVAILABLE_MESSAGE })

  const source = readFileSync(new URL('../src/main.jsx', import.meta.url), 'utf8')
  assert.match(source, /bootstrapError/)
  assert.match(source, /<UnavailablePage/)
  assert.match(source, /onRetry=\{retryStartup\}/)
})

test('route capabilities match platform and tenant role boundaries', () => {
  assert.deepEqual(deriveCapabilities({ role: 'Student' }, 'student'), {
    platformAdmin: false, tenantInstructor: false, tenantAdmin: false,
  })
  assert.deepEqual(deriveCapabilities({ role: 'Student' }, 'instructor'), {
    platformAdmin: false, tenantInstructor: true, tenantAdmin: false,
  })
  assert.deepEqual(deriveCapabilities({ role: 'Student' }, 'owner'), {
    platformAdmin: false, tenantInstructor: true, tenantAdmin: true,
  })
  assert.deepEqual(deriveCapabilities({ role: 'Admin' }, null), {
    platformAdmin: true, tenantInstructor: true, tenantAdmin: true,
  })

  const source = readFileSync(new URL('../src/main.jsx', import.meta.url), 'utf8')
  assert.match(source, /path='\/classroom'.*capability='tenantInstructor'/)
  assert.match(source, /path='\/admin\/groups'.*capability='tenantAdmin'/)
  assert.match(source, /path='\/admin\/users'.*capability='platformAdmin'/)
  assert.match(source, /path='\/admin\/templates'.*capability='platformAdmin'/)
})

test('routed Templates page uses valid OpenAPI operations and obsolete pages stay removed', () => {
  const contract = JSON.parse(readFileSync(new URL('../openapi.json', import.meta.url), 'utf8'))
  assert.ok(contract.paths['/api/admin/templates']?.get)
  assert.ok(contract.paths['/api/admin/templates']?.post)

  for (const page of ['ValidationPage.jsx', 'SettingsPage.jsx', 'ProxmoxPage.jsx']) {
    assert.equal(existsSync(new URL(`../src/pages/${page}`, import.meta.url)), false)
  }
})

test('password reset uses an accessible masked confirmation dialog instead of prompt', () => {
  const source = readFileSync(new URL('../src/pages/UsersPage.jsx', import.meta.url), 'utf8')
  assert.doesNotMatch(source, /\bprompt\s*\(/)
  assert.match(source, /role='dialog'/)
  assert.match(source, /aria-modal='true'/)
  assert.match(source, /id='reset-password'.*type='password'/)
  assert.match(source, /id='reset-password-confirmation'.*type='password'/)
  assert.match(source, /Passwords do not match/)
})

test('top-level render is protected by a recovery error boundary', () => {
  const source = readFileSync(new URL('../src/main.jsx', import.meta.url), 'utf8')
  assert.match(source, /render\(<ErrorBoundary><App \/><\/ErrorBoundary>\)/)
})
