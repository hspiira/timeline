/**
 * Whether a permission list grants resource:action, honouring the same "resource:*"
 * and "*:*" wildcards the API applies.
 *
 * Decides what the interface offers, not what is allowed: every endpoint re-checks.
 */
export function hasPermission(
  permissions: string[] | undefined,
  resource: string,
  action: string
): boolean {
  if (!permissions?.length) return false
  return (
    permissions.includes(`${resource}:${action}`) ||
    permissions.includes(`${resource}:*`) ||
    permissions.includes('*:*')
  )
}
