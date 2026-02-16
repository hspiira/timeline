import { useState, useEffect } from 'react'

/**
 * Determines if the current user has subject erasure permission.
 * Used to hide the Erase / Anonymize button on subject detail when the user lacks permission.
 *
 * TODO: When backend exposes permissions (e.g. in /auth/me or a safe probe endpoint
 * that returns 403 when lacking subject.erasure), implement a real check here.
 * Until then we return true when enabled so the button stays visible; 403 on click
 * is handled in the subject detail page.
 */
export function useHasSubjectErasureAccess(enabled: boolean): boolean | null {
  const [hasAccess, setHasAccess] = useState<boolean | null>(null)

  useEffect(() => {
    if (!enabled) {
      setHasAccess(null)
      return
    }
    setHasAccess(true)
  }, [enabled])

  return hasAccess
}
