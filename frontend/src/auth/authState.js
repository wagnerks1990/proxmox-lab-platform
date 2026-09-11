export const AUTH_UNAVAILABLE_MESSAGE = 'LabGoblin cannot reach the authentication service. Check the server connection and try again.'

export function classifyAuthFailure(error) {
  if (error?.response?.status === 401) return { user: false, error: null }
  return { user: null, error: AUTH_UNAVAILABLE_MESSAGE }
}
