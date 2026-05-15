export default function ActivityFeed({ rows = [] }) {
  return <div className='panel'><h4>Recent Activity</h4><div className='activity-feed'>{rows.length ? rows.map(r => <div key={r.id} className='activity-item'>{r.protocol} · {r.status} · {r.created_at || '-'}</div>) : <div className='muted'>No activity yet.</div>}</div></div>
}
