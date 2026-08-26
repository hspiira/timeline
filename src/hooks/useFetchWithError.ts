import { useCallback, useState } from 'react'
import { getApiErrorDisplay, isAuthOrPermissionError } from '@/lib/api-utils'

export interface UseFetchWithErrorOptions {
  defaultErrorMessage?: string
  /** If false, refetch will no-op until enabled becomes true. Caller can still call refetch() when ready. */
  enabled?: boolean
}

export interface UseFetchWithErrorResult<T> {
  data: T | null
  error: string | null
  loading: boolean
  hasNoAccess: boolean
  refetch: () => Promise<void>
  setError: (message: string | null) => void
}

/**
 * Runs an async fetcher that returns { data, error?, response? } (e.g. timelineApi.*.list()).
 * Handles loading, error via getApiErrorDisplay, and hasNoAccess via isAuthOrPermissionError.
 */
export function useFetchWithError<T>(
  fetcher: () => Promise<{ data?: T | null; error?: unknown; response?: Response }>,
  options: UseFetchWithErrorOptions = {},
): UseFetchWithErrorResult<T> {
  const { defaultErrorMessage = 'An error occurred', enabled = true } = options
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [hasNoAccess, setHasNoAccess] = useState(false)

  const refetch = useCallback(async () => {
    if (!enabled) return

    setLoading(true)
    setError(null)
    setHasNoAccess(false)

    try {
      const result = await fetcher()

      if (result.error != null) {
        const display = getApiErrorDisplay(
          { error: result.error, status: result.response?.status },
          defaultErrorMessage,
        )
        const noAccess = isAuthOrPermissionError(display, result.response?.status)
        setHasNoAccess(noAccess)
        setError(noAccess ? null : display.message)
        setData(null)
      } else if (result.data !== undefined) {
        setData(result.data ?? null)
      }
    } catch (err) {
      const display = getApiErrorDisplay({ error: err }, defaultErrorMessage)
      setError(display.message)
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [fetcher, defaultErrorMessage, enabled])

  return { data, error, loading, hasNoAccess, refetch, setError }
}
