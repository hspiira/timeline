/**
 * Route-level auth guard for TanStack Router.
 * Use as beforeLoad on protected routes to redirect unauthenticated users to login
 * before any component or loader runs (no token in localStorage = redirect).
 */

import { redirect } from '@tanstack/react-router'
import { getAuthToken } from './api-client'

export function requireAuthBeforeLoad() {
  const token = getAuthToken()
  if (!token) {
    throw redirect({
      to: '/login',
      search: { tenant: '' },
      replace: true,
    })
  }
}
