import { useStore } from '@tanstack/react-store'
import { authStore } from '@/lib/auth-store'
import { hasPermission } from '@/lib/permissions'

/**
 * Whether the signed-in user holds subject:export, so the Export button can be
 * hidden rather than fail on click. Null means not yet known, not denied.
 */
export function useHasSubjectExportAccess(enabled: boolean): boolean | null {
  const user = useStore(authStore, (s) => s.user)
  if (!enabled || !user) return null
  return hasPermission(user.permissions, 'subject', 'export')
}
