import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getPool, planPool } from '../services/poolsApi'
import StatCard from '../components/operational/StatCard'

export default function PoolDetailPage(){
 const { id } = useParams()
 const [pool,setPool]=useState(null)
 const [plan,setPlan]=useState(null)
 useEffect(()=>{ if(!id) return; getPool(id).then(setPool); planPool(id).then(setPlan)},[id])
 return <section><h2>Pool Detail</h2><p className='muted'>Planning only — no VMs will be changed.</p><div className='group'><StatCard label='Pool' value={pool?.name}/><StatCard label='Desired Size' value={plan?.desired_size}/><StatCard label='Warnings' value={plan?.warnings?.length||0}/></div><table className='vm-table'><thead><tr><th>VMID Preview</th><th>Naming Preview</th></tr></thead><tbody>{(plan?.vmid_preview||[]).map((v,i)=><tr key={v}><td>{v}</td><td>{plan?.naming_preview?.[i]}</td></tr>)}</tbody></table></section>
}
