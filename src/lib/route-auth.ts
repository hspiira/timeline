/**
 * Route-level auth guard for TanStack Router.
 * Use as beforeLoad on protected routes to redirect unauthenticated users to login
 * before any component or loader runs (no token in localStorage = redirect).
 *
 * On the server (SSR) we never redirect: there is no localStorage, so we'd always
 * redirect. Let the client run after hydration; it will have the token and stay on
 * the page, or redirect to login if there's no token.
 *
 * Pass the path this route is protecting as `intendedPath` so we never use
 * window.location (which can still be /login when navigating from login to /),
 * avoiding redirect param compounding.
 */
import { redirect } from '@tanstack/react-router'
import { getAuthToken } from './api-client'

function safeRedirectPath(path: string): string {
  const p = path?.trim() || '/'
  if (p === '/login' || p === '/register' || p === '/set-password') {
    return '/'
  }
  return p.startsWith('/') && !p.startsWith('//') ? p : '/'
}

export function requireAuthBeforeLoad(intendedPath?: string) {
  if (typeof window === 'undefined') {
    return
  }
  const token = getAuthToken()
  if (!token) {
    const redirectPath = safeRedirectPath(
      intendedPath ?? window.location.pathname
    )
    throw redirect({
      to: '/login',
      search: { tenant: '', redirect: redirectPath },
      replace: true,
    })
  }
}
