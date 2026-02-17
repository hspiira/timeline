import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { Plus, Activity, Calendar, ChevronLeft, ChevronRight } from 'lucide-react'
import { LoadingIcon, ErrorIcon } from '@/components/ui/icons'
import { useEffect, useState } from 'react'
import { useStore } from '@tanstack/react-store'
import { timelineApi } from '@/lib/api-client'
import { authStore } from '@/lib/auth-store'
import { EventDocumentsModal } from '@/components/documents/EventDocumentsModal'
import { EventDetailsModal } from '@/components/events/EventDetailsModal'
import { EventsTable } from '@/components/events/EventsTable'
import { EmptyState } from '@/components/ui/EmptyState'
import type { EventResponse, EventListResponse } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'

const EVENTS_PAGE_SIZE_OPTIONS = [10, 20, 50]
const DEFAULT_EVENTS_PAGE_SIZE = 20

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
  const [pageSize, setPageSize] = useState(DEFAULT_EVENTS_PAGE_SIZE)
  const [totalCount, setTotalCount] = useState<number | null>(null)

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authState.isLoading && !authState.user) {
      navigate({ to: '/login', search: { tenant: '' } })
    }
  }, [authState.isLoading, authState.user, navigate])

  // Reset to first page when filter changes
  useEffect(() => {
    setPage(0)
  }, [filterEventType])

  useEffect(() => {
    if (authState.user) {
      fetchEvents()
    }
  }, [filterEventType, authState.user, page, pageSize])

  const fetchEvents = async () => {
    setLoading(true)
    setError(null)
    try {
      // Load all registered event types from schemas (so filter shows every type, not only those with events)
      const schemaRes = await timelineApi.eventSchemas.list({ limit: 500 })
      const schemaList = Array.isArray(schemaRes.data) ? schemaRes.data : []
      const types: string[] = [...new Set(schemaList.map((s) => s.event_type).filter((x): x is string => Boolean(x)))]
      setEventTypes(types)

      const listParams = {
        skip: page * pageSize,
        limit: pageSize,
        ...(filterEventType ? { event_type: filterEventType } : {}),
      }
      const [{ data: listData, error: apiError }, countRes] = await Promise.all([
        timelineApi.events.listAll(listParams),
        timelineApi.events.count(),
      ])

      if (apiError) {
        const errorMessage =
          (apiError as { message?: string })?.message || 'Unable to connect to the server'
        setError(errorMessage)
        console.error('API error:', apiError)
      } else if (listData) {
        // Total count is only accurate when not filtering by event_type
        setTotalCount(filterEventType ? null : (countRes.data?.total ?? null))

        // Fetch full event details (needed for EventsTable payload display)
        const fullEvents = await Promise.all(
          listData.map(async (item: EventListResponse) => {
            const { data } = await timelineApi.events.get(item.id)
            return data
          })
        )
        const validEvents = fullEvents.filter((e): e is EventResponse => e != null)
        setEvents(validEvents)

        const uniqueSubjectIds = [...new Set(validEvents.map((e) => e.subject_id))]

        // Load document counts and subject display names for current page in parallel
        const [documentResults, subjectResults] = await Promise.all([
          Promise.all(
            listData.map(async (item: EventListResponse) => {
              try {
                const { data: docs, error } = await timelineApi.documents.listByEvent(item.id)
                if (error) {
                  console.warn(`API error loading documents for event ${item.id}:`, error)
                  return { eventId: item.id, count: 0 }
                }
                return { eventId: item.id, count: Array.isArray(docs) ? docs.length : 0 }
              } catch (err) {
                console.error(`Failed to load documents for event ${item.id}:`, err)
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

        const counts: Record<string, number> = {}
        documentResults.forEach(({ eventId, count }) => {
          counts[eventId] = count
        })
        setDocumentCounts(counts)

        const names: Record<string, string> = {}
        subjectResults.forEach(({ subjectId, displayName }) => {
          names[subjectId] = displayName
        })
        setSubjectDisplayNames(names)
      }
    } catch (err) {
      setError('An unexpected error occurred')
      console.error('Error:', err)
    } finally {
      setLoading(false)
    }
  }

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
            onClick={fetchEvents}
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
    <>
      {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div>
            <h1 className="text-lg font-bold text-foreground mb-0.5">
              Events
            </h1>
            <p className="text-sm text-muted-foreground">
              Browse and manage all timeline events
            </p>
          </div>
          <Button onClick={() => navigate({ to: '/events/create' })} variant="primary" size="sm">
            <Plus className="w-4 h-4" />
            Log Event
          </Button>
        </div>

        {/* Filters */}
        {eventTypes.length > 0 && (
          <div className="bg-card/80 backdrop-blur-sm rounded-none p-2.5 border border-border/50 mb-3">
            <div className="flex flex-wrap items-center gap-2">
              <label className="text-sm font-medium text-foreground/90">
                Filter by type:
              </label>
              <Select
                value={filterEventType}
                onChange={(e) => setFilterEventType(e.target.value)}
                className="px-2.5 py-1 bg-background border border-input rounded-none text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">All Event Types</option>
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
                >
                  Clear filter
                </Button>
              )}
            </div>
          </div>
        )}

        {/* Empty State or Events Timeline */}
        {events.length === 0 ? (
          <div className="bg-card/80 backdrop-blur-sm rounded-none border border-border/50">
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
          <div className="bg-card/80 backdrop-blur-sm rounded-none border border-border/60 overflow-hidden">
            <h2 className="font-display text-xs font-semibold uppercase tracking-wider text-muted-foreground px-4 pt-4 pb-2 border-b border-border/60">
              Events
            </h2>
            <div className="p-4">
            <EventsTable
              events={events}
              documentCounts={documentCounts}
              showSubjectColumn
              subjectDisplayNames={subjectDisplayNames}
              onViewDetails={(e) => setDetailsEventId(e.id)}
              onViewDocuments={(e) => setSelectedEventId(e.id)}
            />
            </div>
            {/* Pagination */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-3 border-t border-border/60 bg-[var(--dashboard-accent-muted)]/20">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span>Show</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value))
                    setPage(0)
                  }}
                  className="bg-background border border-input rounded-none text-foreground px-2.5 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  {EVENTS_PAGE_SIZE_OPTIONS.map((size) => (
                    <option key={size} value={size}>
                      {size}
                    </option>
                  ))}
                </select>
                <span>per page</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span>
                  {totalCount !== null
                    ? `${page * pageSize + 1}–${Math.min((page + 1) * pageSize, totalCount)} of ${totalCount}`
                    : `${page * pageSize + 1}–${page * pageSize + events.length}`}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <Button
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                  variant="ghost"
                  size="sm"
                  title="Previous page"
                  aria-label="Previous page"
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="px-2 text-sm text-muted-foreground">
                  {totalCount !== null
                    ? `Page ${page + 1} of ${Math.ceil(totalCount / pageSize) || 1}`
                    : `Page ${page + 1}`}
                </span>
                <Button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={
                    totalCount !== null
                      ? (page + 1) * pageSize >= totalCount
                      : events.length < pageSize
                  }
                  variant="ghost"
                  size="sm"
                  title="Next page"
                  aria-label="Next page"
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
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
                // Refresh documents
                setSelectedEventId(null)
                fetchEvents()
              }}
            />
          ) : null
        })()}

        {/* Details Modal */}
        {detailsEventId && events.length > 0 && (() => {
          const event = events.find(e => e.id === detailsEventId)
          return event ? (
            <EventDetailsModal
              event={event}
              onClose={() => setDetailsEventId(null)}
            />
          ) : null
        })()}

    </>
  )
}
