import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

test('API client uses cookies and never reads a JWT from browser storage', () => {
  const source = readFileSync(new URL('../src/api/client.js', import.meta.url), 'utf8')
  assert.match(source, /withCredentials:\s*true/)
  assert.doesNotMatch(source, /getItem\(['"]token['"]\)/)
})

test('console launch code never puts auth or Proxmox tickets in a URL', () => {
  const eventStream = readFileSync(new URL('../src/hooks/useEventStream.js', import.meta.url), 'utf8')
  const vmPage = readFileSync(new URL('../src/pages/VmsPage.jsx', import.meta.url), 'utf8')
  assert.doesNotMatch(eventStream, /token=/)
  assert.doesNotMatch(vmPage, /ticket=/)
})
