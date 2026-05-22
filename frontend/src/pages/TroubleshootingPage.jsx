import { useEffect, useState } from 'react'
import { getTroubleshootingRecent } from '../services/troubleshootingApi'
import useOperationalEvents from '../hooks/useOperationalEvents'
import { useOperationalStore } from '../state/operationalStore'

export default function TroubleshootingPage(){
 const [rows,setRows]=useState([])
 const live=useOperationalStore()
 useOperationalEvents()
 useEffect(()=>{getTroubleshootingRecent().then((data)=>setRows(Array.isArray(data)?data:[])).catch(()=>setRows([]))},[])
 return <section><h2>Troubleshooting</h2><div className='muted'>Live stream: {live.connected ? 'connected' : live.status}</div>{rows.length===0?<p className='muted'>No active issues detected.</p>:null}<div className='group'>{rows.map((r,i)=><div key={i} className='panel'><h4>{r.title||r.issue_type}</h4><div className='muted'>{r.category} • {r.subsystem}</div><div>Severity: {r.severity}</div><div>Cause: {r.probable_cause}</div><div>Fix: {r.suggested_fix}</div></div>)}</div></section>
}
