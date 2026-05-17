export default function ConsoleStatusBanner({ status }) { if(!status||status==='idle') return null; return <div className='muted'>Console status: {status}</div> }
