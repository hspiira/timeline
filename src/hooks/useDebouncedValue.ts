import { useState, useEffect, useRef } from 'react'

/**
 * Returns a value that updates after the given delay when the source value changes.
 * Use for debouncing API calls or expensive updates (e.g. search inputs).
 */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current)
    timeoutRef.current = setTimeout(() => {
      setDebouncedValue(value)
      timeoutRef.current = null
    }, delayMs)
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    }
  }, [value, delayMs])

  return debouncedValue
}
