export default function OrganizationSwitcher({ organizations, organizationId, onChange, compact = false }) {
  if (!organizations.length) return null
  return <label className={`organization-switcher${compact ? ' organization-switcher-compact' : ''}`}>
    <span className='organization-switcher-label'>Organization</span>
    <select value={organizationId} onChange={onChange} aria-label='Current organization'>
      <option value='' disabled>Select an organization</option>
      {organizations.map(organization => <option key={organization.id} value={organization.id}>{organization.name}</option>)}
    </select>
  </label>
}
