import { useStore } from '@tanstack/react-store'
import { authStore } from '@/lib/auth-store'
import { hasPermission } from '@/lib/permissions'

/**
 * Reports whether the signed-in user holds subject:erasure, so the subject detail
 * page can hide the Erase / Anonymize button rather than offer an action that fails.
 *
 * Returns null while disabled or before the user has loaded, which callers treat
 * as "not yet known" and distinct from a denial.
 */
export function useHasSubjectErasureAccess(enabled: boolean): boolean | null {
  const user = useStore(authStore, (s) => s.user)
  if (!enabled || !user) return null
  return hasPermission(user.permissions, 'subject', 'erasure')
}
