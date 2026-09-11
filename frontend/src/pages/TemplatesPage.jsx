import { useEffect, useMemo, useState } from 'react'
import api from '../services/api'

const emptyTemplate = { name: '', proxmox_node: '', source_vmid: '', enabled: true }

const errorDetail = error => {
  const detail = error?.response?.data?.detail
  return typeof detail === 'string' ? detail : JSON.stringify(detail || 'Request failed.')
}

export default function TemplatesPage({ setMessage }) {
  const [rows, setRows] = useState([])
  const [nodeFilter, setNodeFilter] = useState('')
  const [form, setForm] = useState(emptyTemplate)
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState(null)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await api.get('/admin/templates')
      setRows(Array.isArray(response.data) ? response.data : [])
    } catch (requestError) {
      setRows([])
      setError(errorDetail(requestError))
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { load() }, [])

  const create = async event => {
    event.preventDefault()
    try {
      await api.post('/admin/templates', {
        name: form.name.trim(),
        proxmox_node: form.proxmox_node.trim(),
        source_vmid: Number(form.source_vmid),
        enabled: form.enabled,
      })
      setMessage({ type: 'success', text: 'Template registered.' })
      setForm(emptyTemplate)
      await load()
    } catch (requestError) {
      setMessage({ type: 'error', text: errorDetail(requestError) })
    }
  }

  const toggleEnabled = async template => {
    setBusyId(template.id)
    try {
      await api.patch(`/admin/templates/${template.id}`, { enabled: !template.enabled })
      setMessage({ type: 'success', text: `${template.name} ${template.enabled ? 'disabled' : 'enabled'}.` })
      await load()
    } catch (requestError) {
      setMessage({ type: 'error', text: errorDetail(requestError) })
    } finally {
      setBusyId(null)
    }
  }

  const visibleRows = useMemo(() => rows.filter(template =>
    !nodeFilter || String(template.proxmox_node || '').toLowerCase().includes(nodeFilter.toLowerCase())
  ), [nodeFilter, rows])

  return <section className='page-shell' aria-labelledby='templates-title'>
    <header className='ui-page-header'>
      <div><p className='muted'>Infrastructure</p><h2 id='templates-title'>Templates</h2><p className='ui-page-header__description'>Register existing Proxmox templates for controlled LabGoblin assignment.</p></div>
    </header>

    <section className='panel' aria-labelledby='create-template-title'>
      <h3 id='create-template-title'>Register template</h3>
      <p className='muted'>The VM must already be converted to a template on the selected Proxmox node.</p>
      <form className='ui-form-grid' onSubmit={create}>
        <label className='ui-field'>Name<input value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} required /></label>
        <label className='ui-field'>Proxmox node<input value={form.proxmox_node} onChange={event => setForm({ ...form, proxmox_node: event.target.value })} required /></label>
        <label className='ui-field'>Source VMID<input type='number' min='100' inputMode='numeric' value={form.source_vmid} onChange={event => setForm({ ...form, source_vmid: event.target.value })} required /></label>
        <label className='ui-checkbox'><input type='checkbox' checked={form.enabled} onChange={event => setForm({ ...form, enabled: event.target.checked })} />Available for assignments</label>
        <div className='ui-cluster ui-form-grid__wide'><button type='submit' disabled={!form.name.trim() || !form.proxmox_node.trim() || !form.source_vmid}>Register template</button></div>
      </form>
    </section>

    <section className='panel' aria-labelledby='template-list-title'>
      <div className='panel-head'><div><h3 id='template-list-title'>Registered templates</h3><p className='muted'>{visibleRows.length} shown</p></div><button type='button' className='ui-button--secondary' onClick={load} disabled={loading}>{loading ? 'Refreshing…' : 'Refresh'}</button></div>
      <label className='ui-field'>Filter by node<input type='search' value={nodeFilter} onChange={event => setNodeFilter(event.target.value)} /></label>
      {error ? <p className='msg error' role='alert'>{error}</p> : null}
      {loading ? <p className='muted' role='status'>Loading templates…</p> : null}
      {!loading && !error && visibleRows.length === 0 ? <p className='muted'>No templates match the current filter.</p> : null}
      {visibleRows.length > 0 ? <div className='ui-table-wrap' role='region' aria-labelledby='template-list-title' tabIndex='0'>
        <table className='ui-table'><thead><tr><th scope='col'>Name</th><th scope='col'>Node</th><th scope='col'>VMID</th><th scope='col'>Availability</th><th scope='col'>Action</th></tr></thead><tbody>{visibleRows.map(template => <tr key={template.id}><th scope='row'>{template.name}</th><td>{template.proxmox_node}</td><td>{template.source_vmid}</td><td><span className={`ui-status-badge ui-status-badge--${template.enabled ? 'success' : 'neutral'}`}>{template.enabled ? 'Enabled' : 'Disabled'}</span></td><td><button type='button' className='ui-button--secondary' disabled={busyId === template.id} aria-label={`${template.enabled ? 'Disable' : 'Enable'} ${template.name}`} onClick={() => toggleEnabled(template)}>{busyId === template.id ? 'Saving…' : template.enabled ? 'Disable' : 'Enable'}</button></td></tr>)}</tbody></table>
      </div> : null}
    </section>
  </section>
}
