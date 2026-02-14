import { useState, useCallback } from 'react'

export interface UseFormSubmitOptions<T> {
  onSuccess?: (result: T) => void
  onError?: (err: unknown) => void
}

export interface UseFormSubmitReturn {
  /** Run an async submit function with loading/error handling. Returns the result or undefined on throw. */
  execute: <T>(fn: () => Promise<T>) => Promise<T | undefined>
  loading: boolean
  error: string | null
  setError: (message: string | null) => void
  clearError: () => void
}

export function useFormSubmit(options?: UseFormSubmitOptions<unknown>): UseFormSubmitReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const clearError = useCallback(() => setError(null), [])

  const execute = useCallback(
    async <T>(fn: () => Promise<T>): Promise<T | undefined> => {
      setError(null)
      setLoading(true)
      try {
        const result = await fn()
        options?.onSuccess?.(result as unknown)
        return result
      } catch (err) {
        const message = err instanceof Error ? err.message : 'An error occurred'
        setError(message)
        options?.onError?.(err)
        return undefined
      } finally {
        setLoading(false)
      }
    },
    [options]
  )

  return { execute, loading, error, setError, clearError }
}
