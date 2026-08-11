/**
 * Route-level auth guard for TanStack Router.
 * Use as beforeLoad on protected routes to redirect unauthenticated users to login.
 * Token is in memory only; on the client we run rehydration (refresh from httpOnly cookie)
 * before checking so that refresh keeps the session.
 *
 * On the server (SSR) we never redirect; the client will run rehydration after hydration.
 */
import { redirect } from '@tanstack/react-router'
import { getAuthToken } from './api-client'
import { authActions } from './auth-store'

function safeRedirectPath(path: string): string {
  const p = path?.trim() || '/'
  if (p === '/login' || p === '/register' || p === '/set-password') {
    return '/'
  }
  return p.startsWith('/') && !p.startsWith('//') ? p : '/'
}

export async function requireAuthBeforeLoad(intendedPath?: string) {
  if (typeof window === 'undefined') {
    return
  }
  await authActions.initAuth()
  const token = getAuthToken()
  if (!token) {
    const redirectPath = safeRedirectPath(
      intendedPath ?? window.location.pathname
    )
    throw redirect({
      to: '/login',
      search: { redirect: redirectPath },
      replace: true,
    })
  }
}
