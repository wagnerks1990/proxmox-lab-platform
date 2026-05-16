export default function ReconnectBanner({ status }) { return status==='reconnecting' ? <div className='badge badge-provisioning'>Reconnecting session...</div> : null }
