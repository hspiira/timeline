import { useCallback, useEffect, useRef, useState } from 'react'
import { timelineApi } from '@/lib/api-client'
import type { EventListResponse, EventResponse } from '@/lib/types'

export const EVENTS_PAGE_SIZE = 20

const getApiErrorMessage = (err: unknown): string =>
  (err as { message?: string })?.message ?? 'Unable to connect to the server'

export interface UseEventsListOptions {
  /** When false, no fetch runs (e.g. user not authenticated). */
  enabled: boolean
  filterEventType: string
  /** When true, fetch only the given page (no infinite scroll). Parent controls page. */
  paged?: boolean
  /** Current page (0-based). Used when paged is true. */
  page?: number
}

export interface UseEventsListResult {
  events: EventResponse[]
  loading: boolean
  error: string | null
  documentCounts: Record<string, number>
  subjectDisplayNames: Record<string, string>
  hasMore: boolean
  loadingMore: boolean
  totalCount: number | null
  loadMore: () => void
  refetch: () => void
}

/**
 * Single responsibility: fetch and paginate events list plus document counts and subject names.
 * Used by the events page; keeps data logic out of the UI component (SRP).
 */
export function useEventsList(options: UseEventsListOptions): UseEventsListResult {
  const { enabled, filterEventType, paged = false, page: pagedPage = 0 } = options
  const [events, setEvents] = useState<EventResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [documentCounts, setDocumentCounts] = useState<Record<string, number>>({})
  const [subjectDisplayNames, setSubjectDisplayNames] = useState<Record<string, string>>({})
  const [page, setPage] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [totalCount, setTotalCount] = useState<number | null>(null)
  const [refetchTrigger, setRefetchTrigger] = useState(0)
  const loadingMoreRef = useRef(false)
  const hasMoreRef = useRef(true)

  const effectivePage = paged ? pagedPage : page
  const isAppend = !paged && page > 0

  const loadMore = useCallback(() => {
    if (paged) return
    if (loadingMoreRef.current || !hasMoreRef.current) return
    setPage((p) => p + 1)
  }, [paged])

  const refetch = useCallback(() => {
    setPage(0)
    setHasMore(true)
    setRefetchTrigger((t) => t + 1)
  }, [])

  useEffect(() => {
    if (paged) return
    setPage(0)
    setHasMore(true)
  }, [filterEventType, paged])

  useEffect(() => {
    if (!enabled) return
    if (isAppend) {
      loadingMoreRef.current = true
      setLoadingMore(true)
    } else {
      setLoading(true)
    }
    setError(null)
    let cancelled = false

    const run = async () => {
      try {
        const listParams = {
          skip: effectivePage * EVENTS_PAGE_SIZE,
          limit: EVENTS_PAGE_SIZE,
        }
        const promises: [
          Promise<{ data?: EventListResponse[]; error?: unknown }>,
          Promise<{ data?: { total?: number } }>?,
        ] = [timelineApi.events.listAll(listParams)]
        if (!isAppend || paged) {
          promises.push(timelineApi.events.count())
        }
        const results = await Promise.all(promises)
        const listData = (results[0] as { data?: EventListResponse[]; error?: unknown }).data
        const apiError = (results[0] as { error?: unknown }).error
        const countRes = !isAppend || paged ? results[1] : null

        if (cancelled) return
        if (apiError) {
          setError(getApiErrorMessage(apiError))
          console.error('API error:', apiError)
          return
        }
        if (!listData) return

        const fullEvents = await Promise.all(
          listData.map(async (item: EventListResponse) => {
            const { data } = await timelineApi.events.get(item.id)
            return data
          }),
        )
        const validEvents = fullEvents.filter((e): e is EventResponse => e != null)
        if (cancelled) return

        if (isAppend) {
          setEvents((prev) => {
            const next = [...prev, ...validEvents]
            if (validEvents.length < EVENTS_PAGE_SIZE) setHasMore(false)
            else if (totalCount != null && next.length >= totalCount) setHasMore(false)
            return next
          })
        } else {
          setEvents(validEvents)
          const total = filterEventType ? null : (countRes?.data?.total ?? null)
          if (total != null) setTotalCount(total)
          setHasMore(
            paged
              ? false
              : total != null
                ? validEvents.length < total
                : validEvents.length >= EVENTS_PAGE_SIZE,
          )
        }

        const uniqueSubjectIds = [...new Set(validEvents.map((e) => e.subject_id))]
        const [documentResults, subjectResults] = await Promise.all([
          Promise.all(
            listData.map(async (item: EventListResponse) => {
              try {
                const { data: docs, error: docError } = await timelineApi.documents.listByEvent(
                  item.id,
                )
                if (docError) return { eventId: item.id, count: 0 }
                return { eventId: item.id, count: Array.isArray(docs) ? docs.length : 0 }
              } catch {
                return { eventId: item.id, count: 0 }
              }
            }),
          ),
          Promise.all(
            uniqueSubjectIds.map(async (subjectId) => {
              const { data } = await timelineApi.subjects.get(subjectId)
              return { subjectId, displayName: data?.display_name ?? subjectId }
            }),
          ),
        ])
        if (cancelled) return

        const counts: Record<string, number> = {}
        documentResults.forEach(({ eventId, count }) => {
          counts[eventId] = count
        })
        const names: Record<string, string> = {}
        subjectResults.forEach(({ subjectId, displayName }) => {
          names[subjectId] = displayName
        })

        if (isAppend) {
          setDocumentCounts((prev) => ({ ...prev, ...counts }))
          setSubjectDisplayNames((prev) => ({ ...prev, ...names }))
        } else {
          setDocumentCounts(counts)
          setSubjectDisplayNames(names)
        }
      } catch (err) {
        if (!cancelled) {
          setError('An unexpected error occurred')
          console.error('Error:', err)
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
          setLoadingMore(false)
          loadingMoreRef.current = false
        }
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [enabled, filterEventType, effectivePage, refetchTrigger, isAppend, paged])

  hasMoreRef.current = hasMore
  loadingMoreRef.current = loadingMore

  return {
    events,
    loading,
    error,
    documentCounts,
    subjectDisplayNames,
    hasMore,
    loadingMore,
    totalCount,
    loadMore,
    refetch,
  }
}
