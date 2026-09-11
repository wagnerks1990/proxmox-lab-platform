import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { EmptyState, ErrorState, LoadingState } from '../components/workflows/WorkflowState'
import WorkflowStatus from '../components/workflows/WorkflowStatus'
import { getPool, planPool } from '../services/poolsApi'

const detail = error => {
  const value = error?.response?.data?.detail
  return typeof value === 'string' ? value : 'Pool details could not be loaded.'
}

export default function PoolDetailPage() {
  const { id } = useParams()
  const [pool, setPool] = useState(null)
  const [plan, setPlan] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError('')
    try {
      const [poolResult, planResult] = await Promise.all([getPool(id), planPool(id)])
      setPool(poolResult)
      setPlan(planResult)
    } catch (requestError) {
      setError(detail(requestError))
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { load() }, [load])

  if (loading) return <LoadingState label='Loading pool plan…' />
  if (error) return <ErrorState message={error} onRetry={load} retrying={loading} />

  return <section className='page-shell' aria-labelledby='pool-detail-title'>
    <header className='ui-page-header'>
      <div className='ui-page-header__copy'><p className='muted'>Teaching · Pools</p><h1 id='pool-detail-title' className='ui-page-header__title'>{pool?.name || 'Pool detail'}</h1><p className='ui-page-header__description'>Planning preview only. Viewing this page does not change any virtual machines.</p></div>
      <div className='ui-page-header__actions'><Link className='ui-button ui-button--secondary' to='/pools'>Back to pools</Link><button type='button' onClick={load}>Refresh plan</button></div>
    </header>
    <div className='card-grid' aria-label='Pool summary'>
      <div className='stat-card'><div className='label'>STATUS</div><div className='value'><WorkflowStatus value={pool?.maintenance_mode ? 'maintenance' : pool?.enabled ? 'active' : 'disabled'} /></div></div>
      <div className='stat-card'><div className='label'>DESIRED SIZE</div><div className='value'>{plan?.desired_size ?? 0}</div></div>
      <div className='stat-card'><div className='label'>WARNINGS</div><div className='value'>{plan?.warnings?.length ?? 0}</div></div>
      <div className='stat-card'><div className='label'>TEMPLATE VMID</div><div className='value'>{pool?.template_vmid || '—'}</div></div>
    </div>
    {plan?.warnings?.length ? <section className='ui-alert ui-alert--warning' role='status'><div><strong>Review before provisioning</strong><ul>{plan.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul></div></section> : null}
    <section className='panel' aria-labelledby='pool-preview-title'>
      <h2 id='pool-preview-title'>Planned virtual machines</h2>
      {!plan?.vmid_preview?.length ? <EmptyState title='No VMs in this plan' message='Increase the desired pool size and configure a VMID range to generate a preview.' /> : <div className='ui-table-wrap ui-table-wrap--cards' role='region' aria-labelledby='pool-preview-title' tabIndex='0'><table className='ui-table'><thead><tr><th scope='col'>VMID</th><th scope='col'>Planned name</th></tr></thead><tbody>{plan.vmid_preview.map((vmid, index) => <tr key={vmid}><th scope='row'>{vmid}</th><td>{plan.naming_preview?.[index] || 'Not generated'}</td></tr>)}</tbody></table></div>}
    </section>
    <details className='panel'><summary>Planning checks</summary><ul>{(plan?.estimated_actions || []).map((action, index) => <li key={`${action.action}-${index}`}><strong>{String(action.action).replaceAll('_', ' ')}</strong>: {action.detail}</li>)}</ul></details>
  </section>
}
