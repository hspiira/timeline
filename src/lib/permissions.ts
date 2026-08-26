/**
 * Permission codes as the API grants them: "resource:action", with "resource:*"
 * covering every action on a resource and "*:*" covering everything.
 */

/**
 * Reports whether a permission list grants an action on a resource, honouring the
 * same wildcards the API applies when it gates the endpoint.
 *
 * This decides what the interface offers, never what it is allowed to do. Each
 * endpoint re-checks the caller, so a wrong answer here shows or hides a control
 * rather than granting access.
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
