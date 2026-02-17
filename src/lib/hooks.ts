import { useEffect } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { useStore } from '@tanstack/react-store'
import { authStore } from './auth-store'

/**
 * Redirects authenticated users to the given path (default '/').
 * Used on login/register pages to prevent already-authenticated users from accessing them.
 */
export function useRedirectIfAuthenticated(redirectTo = '/') {
  const navigate = useNavigate()
  const authState = useStore(authStore)

  useEffect(() => {
    if (authState.user) {
      navigate({ to: redirectTo })
    }
  }, [authState.user, navigate, redirectTo])

  // Return whether user is authenticated (useful for conditional rendering)
  return authState.user
}
