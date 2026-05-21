import { useSyncExternalStore } from 'react'

const state = {
  status: 'connecting',
  connected: false,
  error: null,
  tokenExpiry: null,
  events: [],
  debug: {
    lastOnOpenAt: null,
    lastOnMessageAt: null,
    lastHeartbeatAt: null,
    reconnectCount: 0,
    readyState: null,
    transitions: [],
  },
}
const listeners = new Set()

function emit(){ listeners.forEach(l=>l()) }

export function updateOperational(partial){ Object.assign(state, partial); emit() }
export function appendOperationalEvent(event){ state.events = [event, ...state.events].slice(0,50); emit() }
export function updateOperationalDebug(partial){ state.debug = { ...state.debug, ...partial }; emit() }
export function pushOperationalTransition(transition){ state.debug = { ...state.debug, transitions: [transition, ...(state.debug.transitions||[])].slice(0,50) }; emit() }
export function useOperationalStore(){ return useSyncExternalStore((cb)=>{listeners.add(cb); return ()=>listeners.delete(cb)}, ()=>state) }
