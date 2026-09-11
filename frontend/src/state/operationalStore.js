import { useSyncExternalStore } from 'react'

const initialState = {
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
let state = initialState
const listeners = new Set()

function emit(){ listeners.forEach(l=>l()) }

export function getOperationalSnapshot(){ return state }
export function subscribeOperational(listener){ listeners.add(listener); return ()=>listeners.delete(listener) }

export function updateOperational(partial){ state = { ...state, ...partial }; emit() }
export function appendOperationalEvent(event){ state = { ...state, events: [event, ...state.events].slice(0,50) }; emit() }
export function updateOperationalDebug(partial){ state = { ...state, debug: { ...state.debug, ...partial } }; emit() }
export function pushOperationalTransition(transition){ state = { ...state, debug: { ...state.debug, transitions: [transition, ...(state.debug.transitions||[])].slice(0,50) } }; emit() }
export function useOperationalStore(){ return useSyncExternalStore(subscribeOperational, getOperationalSnapshot) }
