import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { Plus, Calendar, Table2, List, FileStack, Search, Filter, X, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'
import { ErrorIcon } from '@/components/ui/icons'
import { useEffect, useState, useRef, useMemo } from 'react'
import { useStore } from '@tanstack/react-store'
import { authStore } from '@/lib/auth-store'
import { EventDocumentsModal } from '@/components/documents/EventDocumentsModal'
import {
  EventDetailsModal,
  EventDetailPanel,
  EventsTable,
  EventsTimeline,
  EventsSearchEmptyMessage,
  EventsLoadingSentinel,
} from '@/components/events'
import { EmptyState } from '@/components/ui/EmptyState'
import { Skeleton } from '@/components/ui/Skeleton'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Combobox,
  ComboboxInput,
  ComboboxContent,
  ComboboxList,
  ComboboxItem,
  ComboboxEmpty,
} from '@/components/ui/combobox'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { useEventsList, EVENTS_PAGE_SIZE, useEventTypes, useIsLg } from '@/hooks'
import { findEventById } from '@/lib/events'
import type { EventResponse } from '@/lib/types'
import { cn } from '@/lib/utils'

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
  const [filterEventType, setFilterEventType] = useState<string>('')
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const [detailsEventId, setDetailsEventId] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'table' | 'timeline'>(getStoredViewMode)
  const [tablePage, setTablePage] = useState(0)
  const [searchQuery, setSearchQuery] = useState('')
  const isLg = useIsLg()
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const sentinelRef = useRef<HTMLDivElement>(null)

  const { types: eventTypes } = useEventTypes()
  const {
    events,
    loading,
    error,
    documentCounts,
    subjectDisplayNames,
    loadingMore,
    loadMore,
    totalCount,
    refetch,
  } = useEventsList({
    enabled: !!authState.user,
    filterEventType,
    paged: viewMode === 'table',
    page: viewMode === 'table' ? tablePage : undefined,
  })

  const totalPages = totalCount != null ? Math.ceil(totalCount / EVENTS_PAGE_SIZE) : 0
  const showPagination = viewMode === 'table' && totalCount != null && totalPages > 1

  const goToPage = (page: number) => {
    if (page >= 0 && page < totalPages) setTablePage(page)
  }

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
      navigate({ to: '/login', search: { tenant: '', redirect: undefined, sessionExpired: false } })
    }
  }, [authState.isLoading, authState.user, navigate])

  // Reset table page when filter changes (table view)
  useEffect(() => {
    if (viewMode === 'table') setTablePage(0)
  }, [filterEventType, viewMode])

  // Infinite scroll: only in timeline view; when sentinel is visible, load next page
  const loadMoreRef = useRef(loadMore)
  loadMoreRef.current = loadMore
  useEffect(() => {
    if (viewMode !== 'timeline') return
    const scrollEl = scrollContainerRef.current
    const sentinel = sentinelRef.current
    if (!scrollEl || !sentinel || events.length === 0) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries[0]?.isIntersecting) return
        loadMoreRef.current()
      },
      { root: scrollEl, rootMargin: '200px', threshold: 0 }
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [viewMode, events.length])

  // Client-side filter by event type (backend does not filter) and search over loaded events
  const filteredEvents = useMemo(() => {
    let list = events
    if (filterEventType) {
      list = list.filter((e) => (e.event_type ?? '') === filterEventType)
    }
    const q = searchQuery.trim().toLowerCase()
    if (!q) return list
    return list.filter((e) => {
      const type = (e.event_type ?? '').toLowerCase()
      const subjectId = (e.subject_id ?? '').toLowerCase()
      const subjectName = (subjectDisplayNames[e.subject_id] ?? '').toLowerCase()
      const payloadStr =
        e.payload != null && typeof e.payload === 'object'
          ? JSON.stringify(e.payload).toLowerCase()
          : ''
      return (
        type.includes(q) ||
        subjectId.includes(q) ||
        subjectName.includes(q) ||
        payloadStr.includes(q)
      )
    })
  }, [events, filterEventType, searchQuery, subjectDisplayNames])

  if (authState.isLoading || loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between mb-3">
          <Skeleton className="h-7 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="space-y-2">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <Skeleton key={i} className="h-12 w-full rounded-none border border-border/50" />
          ))}
        </div>
      </div>
    )
  }

  if (!authState.user) {
    return null
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
          <Button onClick={refetch} variant="primary" size="sm">
            Retry
          </Button>
        </div>
      </div>
    )
  }

  const listProps = {
    events: filteredEvents,
    documentCounts,
    showSubjectColumn: true as const,
    subjectDisplayNames,
    onViewDetails: (e: EventResponse) => setDetailsEventId(e.id),
    onViewDocuments: (e: EventResponse) => setSelectedEventId(e.id),
  }

  return (
    <div className="flex flex-col min-h-0">
      <div className="flex items-center justify-between shrink-0 mb-3">
        <div>
          <h1 className="text-lg font-bold text-foreground mb-0.5">Events</h1>
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
              <span className="inline-flex items-center gap-2">
                <Table2 className="w-4 h-4" />
                Table
              </span>
            </ToggleGroupItem>
            <ToggleGroupItem value="timeline" aria-label="Timeline view">
              <span className="inline-flex items-center gap-2">
                <List className="w-4 h-4" />
                Timeline
              </span>
            </ToggleGroupItem>
          </ToggleGroup>
          <Button onClick={() => navigate({ to: '/events/create' })} variant="primary" size="sm">
            <Plus className="w-4 h-4" />
            Log Event
          </Button>
        </div>
      </div>

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
            'max-h-[calc(100vh-12rem)]'
          )}
        >
          <div className="flex flex-nowrap items-center gap-0 shrink-0 border-b border-border/50 bg-muted/30 overflow-visible">
            {/* Search */}
            <div className="flex items-center min-w-0 px-3 py-2.5">
              <div className="relative w-full min-w-[12rem] max-w-[18rem]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                <Input
                  type="search"
                  placeholder="Search events, subjects, payload…"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="h-9 pl-9 pr-8 bg-background border border-input/80 rounded-none text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
                  size="sm"
                  aria-label="Search events"
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchQuery('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-none text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
                    aria-label="Clear search"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
            {/* Divider + type filter */}
            {eventTypes.length > 0 && (
              <>
                <div className="w-px self-stretch min-h-[1.5rem] bg-border/60" aria-hidden />
                <div className="flex items-center gap-2 pl-3 pr-4 py-2.5">
                  <Filter className="w-4 h-4 text-muted-foreground shrink-0" aria-hidden />
                  <Combobox
                    value={filterEventType || null}
                    onValueChange={(v) => setFilterEventType(v ?? '')}
                    items={eventTypes}
                  >
                    <ComboboxInput
                      placeholder="All types"
                      showTrigger
                      showClear={!!filterEventType}
                      aria-label="Filter by event type"
                      className="min-w-[11rem] max-w-[14rem] h-9 rounded-none border-input/80 bg-background"
                    />
                    <ComboboxContent className="rounded-none">
                      <ComboboxEmpty>No type found.</ComboboxEmpty>
                      <ComboboxList>
                        {(item: string) => (
                          <ComboboxItem key={item} value={item}>
                            {item}
                          </ComboboxItem>
                        )}
                      </ComboboxList>
                    </ComboboxContent>
                  </Combobox>
                </div>
              </>
            )}
          </div>

          {viewMode === 'timeline' && isLg ? (
            <div className="flex flex-1 min-h-0">
              <div className="flex-1 min-w-0 flex flex-col min-h-0 overflow-hidden relative">
                <div ref={scrollContainerRef} className="px-4 pt-4 pb-0 flex-1 min-h-0 overflow-y-auto">
                  {filteredEvents.length === 0 ? (
                    <EventsSearchEmptyMessage />
                  ) : (
                    <EventsTimeline
                      {...listProps}
                      onSelectEvent={(e) => setDetailsEventId(e.id)}
                      selectedEventId={detailsEventId}
                    />
                  )}
                  {/* Sentinel only in timeline view for infinite scroll */}
                  <EventsLoadingSentinel loading={loadingMore} sentinelRef={sentinelRef} />
                </div>
              </div>
              <div className="hidden lg:flex lg:w-[min(420px,36rem)] lg:shrink-0 lg:flex-col lg:min-h-0 lg:overflow-hidden border-l border-border/60">
                {detailsEventId ? (
                  (() => {
                    const event = findEventById(events, detailsEventId)
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
            <div className="flex-1 min-h-0 overflow-hidden relative flex flex-col">
              <div ref={scrollContainerRef} className="flex-1 min-h-0 overflow-y-auto px-4 pt-4 pb-0">
                <div>
                  {filteredEvents.length === 0 ? (
                    <EventsSearchEmptyMessage />
                  ) : viewMode === 'table' ? (
                    <EventsTable {...listProps} />
                  ) : (
                    <EventsTimeline
                      {...listProps}
                      onSelectEvent={(e) => setDetailsEventId(e.id)}
                      selectedEventId={detailsEventId}
                    />
                  )}
                  {/* Sentinel only in timeline view; table view uses pagination below */}
                  {viewMode === 'timeline' && (
                    <EventsLoadingSentinel loading={loadingMore} sentinelRef={sentinelRef} />
                  )}
                </div>
              </div>
              {showPagination && (
                <div className="flex items-center justify-between shrink-0 px-4 py-3 border-t border-border/50 bg-muted/30">
                  <div className="text-xs text-muted-foreground">
                    Showing {tablePage * EVENTS_PAGE_SIZE + 1}–
                    {Math.min((tablePage + 1) * EVENTS_PAGE_SIZE, totalCount ?? 0)} of {totalCount} events
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      onClick={() => goToPage(0)}
                      disabled={tablePage === 0}
                      variant="ghost"
                      size="sm"
                      title="First page"
                    >
                      <ChevronsLeft className="w-4 h-4" />
                    </Button>
                    <Button
                      onClick={() => goToPage(tablePage - 1)}
                      disabled={tablePage === 0}
                      variant="ghost"
                      size="sm"
                      title="Previous page"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </Button>
                    <span className="px-3 text-xs text-foreground">
                      Page {tablePage + 1} of {totalPages}
                    </span>
                    <Button
                      onClick={() => goToPage(tablePage + 1)}
                      disabled={tablePage >= totalPages - 1}
                      variant="ghost"
                      size="sm"
                      title="Next page"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                    <Button
                      onClick={() => goToPage(totalPages - 1)}
                      disabled={tablePage >= totalPages - 1}
                      variant="ghost"
                      size="sm"
                      title="Last page"
                    >
                      <ChevronsRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {selectedEventId && events.length > 0 && (() => {
        const event = findEventById(events, selectedEventId)
        return event ? (
          <EventDocumentsModal
            eventId={event.id}
            subjectId={event.subject_id}
            eventType={event.event_type}
            onClose={() => setSelectedEventId(null)}
            onDocumentsUpdated={() => {
              setSelectedEventId(null)
              refetch()
            }}
          />
        ) : null
      })()}

      {detailsEventId && events.length > 0 && !(viewMode === 'timeline' && isLg) && (() => {
        const event = findEventById(events, detailsEventId)
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
