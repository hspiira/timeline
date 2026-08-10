import { useState, useEffect } from 'react'
import { timelineApi } from '@/lib/api-client'

/**
 * Probes the audit log API once to determine if the current user has audit read permission.
 * Used to hide the Audit log menu item when the user would get 403 on the page.
 */
export function useHasAuditAccess(enabled: boolean): boolean | null {
  const [hasAccess, setHasAccess] = useState<boolean | null>(null)

  useEffect(() => {
    if (!enabled) {
      setHasAccess(null)
      return
    }
    let cancelled = false
    timelineApi.auditLog.list({ skip: 0, limit: 1 }).then((res) => {
      if (cancelled) return
      setHasAccess(res.error == null && res.response?.status !== 403)
    })
    return () => {
      cancelled = true
    }
  }, [enabled])

  return hasAccess
}
