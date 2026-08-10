import { useState, useCallback, useEffect, useRef } from 'react'

interface UseDebouncedSearchOptions {
  delay?: number
  onSearch: (query: string) => void
}

/**
 * Hook for debounced search with configurable delay
 *
 * Usage:
 * ```tsx
 * const { query, setQuery, isSearching } = useDebouncedSearch({
 *   delay: 300,
 *   onSearch: (query) => {
 *     // Perform search with query
 *     setFilter({ search: query })
 *   },
 * })
 *
 * <input
 *   value={query}
 *   onChange={(e) => setQuery(e.target.value)}
 *   placeholder="Search activities..."
 * />
 * ```
 */
export function useDebouncedSearch({
  delay = 300,
  onSearch,
}: UseDebouncedSearchOptions) {
  const [query, setQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Debounced search effect
  useEffect(() => {
    setIsSearching(true)

    // Clear previous timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }

    // Set new timeout for debounced search
    timeoutRef.current = setTimeout(() => {
      onSearch(query)
      setIsSearching(false)
    }, delay)

    // Cleanup function
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [query, delay, onSearch])

  const clearSearch = useCallback(() => {
    setQuery('')
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    onSearch('')
  }, [onSearch])

  return {
    query,
    setQuery,
    isSearching,
    clearSearch,
  }
}

export default useDebouncedSearch
