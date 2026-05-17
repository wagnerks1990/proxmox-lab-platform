export default function ProtocolButton({ label, enabled, reason, onClick, loading }) {
  return <button className='btn proto-btn' disabled={!enabled || loading} title={enabled ? label : reason} onClick={onClick}>
    {loading ? 'Launching…' : label}
  </button>
}
