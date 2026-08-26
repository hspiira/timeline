import { useEffect, useState } from 'react'
import { timelineApi } from '@/lib/api-client'
import { getApiErrorMessage } from '@/lib/api-utils'

function isDefined<T>(x: T): x is NonNullable<T> {
  return Boolean(x)
}

function extractTypesFromSchemaList(data: unknown): string[] {
  if (Array.isArray(data)) {
    return [...new Set(data.map((s: { event_type?: string }) => s.event_type).filter(isDefined))]
  }
  if (
    data &&
    typeof data === 'object' &&
    'items' in data &&
    Array.isArray((data as { items: unknown[] }).items)
  ) {
    const items = (data as { items: { event_type?: string }[] }).items
    return [...new Set(items.map((s) => s.event_type).filter(isDefined))]
  }
  return []
}

export interface UseEventTypesResult {
  types: string[]
  loading: boolean
  error: string | null
}

/**
 * Fetches event types from schemas (with fallback to events list).
 * Use in WorkflowFormModal, EventTypeSelector, and any form that needs event type options.
 */
export function useEventTypes(): UseEventTypesResult {
  const [types, setTypes] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const { data: schemaList, error: schemaError } = await timelineApi.eventSchemas.list({
          limit: 500,
        })
        if (!mounted) return
        const fromSchemas = extractTypesFromSchemaList(schemaList)
        if (fromSchemas.length > 0) {
          setTypes(fromSchemas)
          return
        }
        if (schemaError) {
          setError(getApiErrorMessage(schemaError, 'Failed to load event types'))
        }
        const { data: eventsList } = await timelineApi.events.listAll()
        if (!mounted) return
        if (eventsList && Array.isArray(eventsList)) {
          const fromEvents = [
            ...new Set(
              eventsList.map((e: { event_type?: string }) => e.event_type).filter(isDefined),
            ),
          ]
          if (fromEvents.length > 0) {
            setTypes(fromEvents)
            setError(null)
          }
        }
      } catch (err) {
        if (mounted) {
          setError(getApiErrorMessage(err, 'An unexpected error occurred'))
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }
    load()
    return () => {
      mounted = false
    }
  }, [])

  return { types, loading, error }
}
