export default function StatCard({ label, value }) { return <div className='panel'><div className='muted'>{label}</div><h3>{value ?? '-'}</h3></div> }
