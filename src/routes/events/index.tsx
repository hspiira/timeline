import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { Plus, Activity, Calendar, Table2, List, FileStack, Loader2 } from 'lucide-react'
import { LoadingIcon, ErrorIcon } from '@/components/ui/icons'
import { useEffect, useState, useRef, useCallback } from 'react'
import { useStore } from '@tanstack/react-store'
import { timelineApi } from '@/lib/api-client'
import { authStore } from '@/lib/auth-store'
import { EventDocumentsModal } from '@/components/documents/EventDocumentsModal'
import { EventDetailsModal } from '@/components/events/EventDetailsModal'
import { EventDetailPanel } from '@/components/events/EventDetailPanel'
import { EventsTable } from '@/components/events/EventsTable'
import { EventsTimeline } from '@/components/events/EventsTimeline'
import { EmptyState } from '@/components/ui/EmptyState'
import type { EventResponse, EventListResponse } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { useIsLg } from '@/hooks/useMediaQuery'
import { cn } from '@/lib/utils'

const EVENTS_PAGE_SIZE = 20
const EVENTS_VIEW_STORAGE_KEY = 'events-view-mode'

function getStoredViewMode(): 'table' | 'timeline' {
  if (typeof window === 'undefined') return 'timeline'
  try {
    const v = window.localStorage.getItem(EVENTS_VIEW_STORAGE_KEY)
    if (v === 'table' || v === 'timeline') return v
  } catch {
    // ignore
  }
  return 'timeline'
}

export const Route = createFileRoute('/events/')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  component: EventsPage,
})

function EventsPage() {
  const navigate = useNavigate()
  const authState = useStore(authStore)
  const [events, setEvents] = useState<EventResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterEventType, setFilterEventType] = useState<string>('')
  const [eventTypes, setEventTypes] = useState<string[]>([])
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const [detailsEventId, setDetailsEventId] = useState<string | null>(null)
  const [documentCounts, setDocumentCounts] = useState<Record<string, number>>({})
  const [subjectDisplayNames, setSubjectDisplayNames] = useState<Record<string, string>>({})
  const [page, setPage] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [totalCount, setTotalCount] = useState<number | null>(null)
  const loadingMoreRef = useRef(false)
  const hasMoreRef = useRef(true)
  const [viewMode, setViewMode] = useState<'table' | 'timeline'>(getStoredViewMode)
  const isLg = useIsLg()
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const sentinelRef = useRef<HTMLDivElement>(null)
  const [refetchTrigger, setRefetchTrigger] = useState(0)

  // Persist view mode
  useEffect(() => {
    try {
      window.localStorage.setItem(EVENTS_VIEW_STORAGE_KEY, viewMode)
    } catch {
      // ignore
    }
  }, [viewMode])

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authState.isLoading && !authState.user) {
      navigate({ to: '/login', search: { tenant: '' } })
    }
  }, [authState.isLoading, authState.user, navigate])

  // Reset to first page when filter changes
  useEffect(() => {
    setPage(0)
    setHasMore(true)
  }, [filterEventType])

  useEffect(() => {
    if (!authState.user) return
    const isAppend = page > 0
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
        if (!isAppend) {
          const schemaRes = await timelineApi.eventSchemas.list({ limit: 500 })
          const schemaList = Array.isArray(schemaRes.data) ? schemaRes.data : []
          const types: string[] = [...new Set(schemaList.map((s) => s.event_type).filter((x): x is string => Boolean(x)))]
          setEventTypes(types)
        }

        const listParams = {
          skip: page * EVENTS_PAGE_SIZE,
          limit: EVENTS_PAGE_SIZE,
          ...(filterEventType ? { event_type: filterEventType } : {}),
        }
        const promises: [Promise<{ data?: EventListResponse[]; error?: unknown }>, Promise<{ data?: { total?: number } }>?] = [
          timelineApi.events.listAll(listParams),
        ]
        if (!isAppend) {
          promises.push(timelineApi.events.count())
        }
        const results = await Promise.all(promises)
        const listData = (results[0] as { data?: EventListResponse[]; error?: unknown }).data
        const apiError = (results[0] as { error?: unknown }).error
        const countRes = !isAppend ? results[1] : null

        if (cancelled) return
        if (apiError) {
          const errorMessage =
            (apiError as { message?: string })?.message || 'Unable to connect to the server'
          setError(errorMessage)
          console.error('API error:', apiError)
          return
        }
        if (!listData) return

        const fullEvents = await Promise.all(
          listData.map(async (item: EventListResponse) => {
            const { data } = await timelineApi.events.get(item.id)
            return data
          })
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
            total != null ? validEvents.length < total : validEvents.length >= EVENTS_PAGE_SIZE
          )
        }

        const uniqueSubjectIds = [...new Set(validEvents.map((e) => e.subject_id))]
        const [documentResults, subjectResults] = await Promise.all([
          Promise.all(
            listData.map(async (item: EventListResponse) => {
              try {
                const { data: docs, error } = await timelineApi.documents.listByEvent(item.id)
                if (error) return { eventId: item.id, count: 0 }
                return { eventId: item.id, count: Array.isArray(docs) ? docs.length : 0 }
              } catch {
                return { eventId: item.id, count: 0 }
              }
            })
          ),
          Promise.all(
            uniqueSubjectIds.map(async (subjectId) => {
              const { data } = await timelineApi.subjects.get(subjectId)
              return { subjectId, displayName: data?.display_name ?? subjectId }
            })
          ),
        ])
        if (cancelled) return

        const counts: Record<string, number> = {}
        documentResults.forEach(({ eventId, count }) => { counts[eventId] = count })
        const names: Record<string, string> = {}
        subjectResults.forEach(({ subjectId, displayName }) => { names[subjectId] = displayName })

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
    return () => { cancelled = true }
  }, [filterEventType, authState.user, page, refetchTrigger])

  // Keep refs in sync for observer
  hasMoreRef.current = hasMore
  loadingMoreRef.current = loadingMore

  const loadMore = useCallback(() => {
    if (loadingMoreRef.current || !hasMoreRef.current) return
    setPage((p) => p + 1)
  }, [])

  // Infinite scroll: when sentinel is visible, load next page
  useEffect(() => {
    const scrollEl = scrollContainerRef.current
    const sentinel = sentinelRef.current
    if (!scrollEl || !sentinel || events.length === 0) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries[0]?.isIntersecting) return
        if (loadingMoreRef.current || !hasMoreRef.current) return
        loadMore()
      },
      { root: scrollEl, rootMargin: '200px', threshold: 0 }
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [events.length, loadMore])

  if (authState.isLoading) {
    return (
      <div className="min-h-[calc(100vh-4rem)] bg-background flex items-center justify-center">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Activity className="w-4 h-4 animate-pulse" />
          <span className="text-sm">Loading...</span>
        </div>
      </div>
    )
  }

  if (!authState.user) {
    return null
  }

  if (loading) {
    return (
      <div className="min-h-[calc(100vh-4rem)] bg-background flex items-center justify-center">
        <div className="flex items-center gap-2 text-muted-foreground">
          <LoadingIcon />
          <span className="text-sm">Loading events...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-[calc(100vh-4rem)] bg-background flex items-center justify-center">
        <div className="text-center max-w-md px-4">
          <div className="w-12 h-12 rounded-none bg-red-100 dark:bg-red-900/20 flex items-center justify-center mx-auto mb-2">
            <ErrorIcon className="w-6 h-6 text-red-600 dark:text-red-400" />
          </div>
          <h3 className="text-sm font-semibold text-foreground mb-1">
            Unable to Load Events
          </h3>
          <p className="text-sm text-muted-foreground mb-3">
            {error}. Please check your connection and try again.
          </p>
          <Button
            onClick={() => { setPage(0); setRefetchTrigger((t) => t + 1) }}
            variant="primary"
            size="sm"
          >
            <LoadingIcon />
            Retry
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col min-h-0">
      {/* Page header: fixed, never scrolls */}
      <div className="flex items-center justify-between shrink-0 mb-3">
        <div>
          <h1 className="text-lg font-bold text-foreground mb-0.5">
            Events
          </h1>
          <p className="text-sm text-muted-foreground">
            Browse and manage all timeline events
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ToggleGroup
            type="single"
            value={viewMode}
            onValueChange={(v) => v && (v === 'table' || v === 'timeline') && setViewMode(v)}
            variant="outline"
            size="sm"
          >
            <ToggleGroupItem value="table" aria-label="Table view">
              <Table2 className="w-4 h-4" />
              Table
            </ToggleGroupItem>
            <ToggleGroupItem value="timeline" aria-label="Timeline view">
              <List className="w-4 h-4" />
              Timeline
            </ToggleGroupItem>
          </ToggleGroup>
          <Button onClick={() => navigate({ to: '/events/create' })} variant="primary" size="sm">
            <Plus className="w-4 h-4" />
            Log Event
          </Button>
        </div>
      </div>

      {/* Empty State or Events card — card fills remaining height when we have events */}
      {events.length === 0 ? (
        <div className="bg-card/80 backdrop-blur-sm rounded-none border border-border/50 shrink-0">
          <EmptyState
            icon={Calendar}
            title="No events yet"
            description="Events are recorded actions or state changes tracked in chronological order. Log your first event to build a timeline history."
            action={{
              label: 'Log Your First Event',
              onClick: () => navigate({ to: '/events/create' }),
            }}
          />
        </div>
      ) : (
        <div
          className={cn(
            'bg-card/95 backdrop-blur-sm rounded-none border-x border-t border-border/60 flex flex-col min-h-0 flex-1 overflow-hidden',
            events.length > 0 && 'max-h-[calc(110vh-12rem)]'
          )}
        >
          {/* Container header: filter only */}
          {eventTypes.length > 0 && (
            <div className="flex items-center gap-3 px-4 py-3 border-b border-border/50 shrink-0 bg-muted/20 min-h-[2.75rem] overflow-visible">
              <label className="text-sm font-medium text-muted-foreground whitespace-nowrap leading-normal">
                Filter by type
              </label>
              <Select
                value={filterEventType}
                onChange={(e) => setFilterEventType(e.target.value)}
                className="h-9 min-w-[10rem] px-3 bg-background border border-input rounded-none text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring leading-normal"
              >
                <option value="">All types</option>
                {eventTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </Select>
              {filterEventType && (
                <Button
                  onClick={() => setFilterEventType('')}
                  variant="ghost"
                  size="sm"
                  className="h-9 px-3 text-sm text-muted-foreground hover:text-foreground leading-normal"
                >
                  Clear
                </Button>
              )}
            </div>
          )}

          {viewMode === 'timeline' && isLg ? (
            /* Two-column: only the events list (left) and detail panel (right) scroll independently */
            <div className="flex flex-1 min-h-0">
              <div className="flex-1 min-w-0 flex flex-col min-h-0 overflow-hidden relative">
                <div ref={scrollContainerRef} className="px-4 pt-4 pb-0 flex-1 min-h-0 overflow-y-auto">
                  <EventsTimeline
                    events={events}
                    documentCounts={documentCounts}
                    showSubjectColumn
                    subjectDisplayNames={subjectDisplayNames}
                    onSelectEvent={(e) => setDetailsEventId(e.id)}
                    selectedEventId={detailsEventId}
                    onViewDetails={(e) => setDetailsEventId(e.id)}
                    onViewDocuments={(e) => setSelectedEventId(e.id)}
                  />
                  <div ref={sentinelRef} className="flex items-center justify-center py-2 min-h-[1rem]">
                    {loadingMore && <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />}
                  </div>
                </div>
              </div>
              <div className="hidden lg:flex lg:w-[min(420px,36rem)] lg:shrink-0 lg:flex-col lg:min-h-0 lg:overflow-hidden border-l border-border/60">
                {detailsEventId ? (
                  (() => {
                    const event = events.find((e) => e.id === detailsEventId)
                    return event ? (
                      <EventDetailPanel
                        event={event}
                        onClose={() => setDetailsEventId(null)}
                        className="flex-1 min-h-0 overflow-hidden"
                      />
                    ) : null
                  })()
                ) : (
                  <div className="flex flex-col items-center justify-center gap-2 flex-1 px-4 py-8 text-center text-muted-foreground min-h-0">
                    <FileStack className="w-10 h-10 opacity-40" strokeWidth={1.25} />
                    <p className="text-sm font-medium">Select an event</p>
                    <p className="text-xs max-w-[200px]">
                      Click any event on the timeline to view its details here.
                    </p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1 min-h-0 overflow-hidden relative">
              <div ref={scrollContainerRef} className="flex-1 min-h-0 overflow-y-auto px-4 pt-4 pb-0">
                <div>
                  {viewMode === 'table' ? (
                    <EventsTable
                      events={events}
                      documentCounts={documentCounts}
                      showSubjectColumn
                      subjectDisplayNames={subjectDisplayNames}
                      onViewDetails={(e) => setDetailsEventId(e.id)}
                      onViewDocuments={(e) => setSelectedEventId(e.id)}
                    />
                  ) : (
                    <EventsTimeline
                      events={events}
                      documentCounts={documentCounts}
                      showSubjectColumn
                      subjectDisplayNames={subjectDisplayNames}
                      onSelectEvent={(e) => setDetailsEventId(e.id)}
                      selectedEventId={detailsEventId}
                      onViewDetails={(e) => setDetailsEventId(e.id)}
                      onViewDocuments={(e) => setSelectedEventId(e.id)}
                    />
                  )}
                  <div ref={sentinelRef} className="flex items-center justify-center py-2 min-h-[1rem]">
                    {loadingMore && <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Documents Modal */}
      {selectedEventId && events.length > 0 && (() => {
          const event = events.find(e => e.id === selectedEventId)
          return event ? (
            <EventDocumentsModal
              eventId={event.id}
              subjectId={event.subject_id}
              eventType={event.event_type}
              onClose={() => setSelectedEventId(null)}
              onDocumentsUpdated={() => {
                setSelectedEventId(null)
                setPage(0)
                setRefetchTrigger((t) => t + 1)
              }}
            />
          ) : null
        })()}

      {/* Details Modal: only when not using the side panel (table view or narrow screen) */}
      {detailsEventId && events.length > 0 && !(viewMode === 'timeline' && isLg) && (() => {
          const event = events.find(e => e.id === detailsEventId)
          return event ? (
            <EventDetailsModal
              event={event}
              onClose={() => setDetailsEventId(null)}
            />
          ) : null
        })()}
    </div>
  )
}
