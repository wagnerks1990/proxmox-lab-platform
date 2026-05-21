export default function SessionExpiredNotice({ status }) { return status==='expired' ? <div className='badge badge-error'>Session expired. Relaunch required.</div> : null }
