import { useEffect, useState } from 'react'
import { timelineApi } from '@/lib/api-client'

/**
 * Probes an admin-only API (connectors health) to determine if the current user
 * has system/read (or equivalent) permission. Used to hide Connectors nav and
 * show "No permission" on /connectors when the user would get 403.
 */
export function useHasSystemAccess(enabled: boolean): boolean | null {
  const [hasAccess, setHasAccess] = useState<boolean | null>(null)

  useEffect(() => {
    if (!enabled) {
      setHasAccess(null)
      return
    }
    let cancelled = false
    timelineApi.connectors.health().then((res) => {
      if (cancelled) return
      setHasAccess(res.error == null && res.response?.status !== 403)
    })
    return () => {
      cancelled = true
    }
  }, [enabled])

  return hasAccess
}
