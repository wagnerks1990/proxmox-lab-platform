import { useSyncExternalStore } from 'react'

const state = { status: 'connecting', events: [] }
const listeners = new Set()

export function updateOperational(partial){ Object.assign(state, partial); listeners.forEach(l=>l()) }
export function appendOperationalEvent(event){ state.events = [event, ...state.events].slice(0,50); listeners.forEach(l=>l()) }
export function useOperationalStore(){ return useSyncExternalStore((cb)=>{listeners.add(cb); return ()=>listeners.delete(cb)}, ()=>state) }
