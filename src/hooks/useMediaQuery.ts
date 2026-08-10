import { useState, useEffect } from 'react'

/**
 * Returns true when the given media query matches (e.g. min-width: 1024px for lg).
 * SSR-safe: defaults to false until mounted.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const m = window.matchMedia(query)
    setMatches(m.matches)
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches)
    m.addEventListener('change', handler)
    return () => m.removeEventListener('change', handler)
  }, [query])

  return matches
}

/** True when viewport is at least 1024px (Tailwind lg). */
export function useIsLg(): boolean {
  return useMediaQuery('(min-width: 1024px)')
}
