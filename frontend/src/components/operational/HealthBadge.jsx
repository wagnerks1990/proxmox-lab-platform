export default function HealthBadge({ value }) { return <span className={`badge ${value==='ok'?'badge-running':'badge-error'}`}>{value}</span> }
