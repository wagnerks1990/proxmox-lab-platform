import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getPool, planPool } from '../services/poolsApi'

export default function PoolDetailPage(){
 const { id } = useParams()
 const [pool,setPool]=useState(null)
 const [plan,setPlan]=useState(null)
 useEffect(()=>{ if(!id) return; getPool(id).then(setPool); planPool(id).then(setPlan)},[id])
 return <section><h2>Pool Detail</h2><p className='muted'>Planning only — no VMs will be changed.</p><pre>{JSON.stringify({pool, plan}, null, 2)}</pre></section>
}
