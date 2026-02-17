import { useMemo } from 'react'
import { Link } from '@tanstack/react-router'
import { FileText, Eye, ArrowUpRight } from 'lucide-react'
import type { EventResponse } from '@/lib/types'
import {
  formatEventDate,
  formatEventTimeWithSeconds,
} from '@/lib/format-date'
import { cn } from '@/lib/utils'

export interface EventsTimelineProps {
  events: EventResponse[]
  documentCounts?: Record<string, number>
  showSubjectColumn?: boolean
  subjectDisplayNames?: Record<string, string>
  /** When set, clicking the event row selects it (e.g. for side panel on wide screens). */
  onSelectEvent?: (event: EventResponse) => void
  /** ID of the event currently selected for detail view. */
  selectedEventId?: string | null
  onViewDetails?: (event: EventResponse) => void
  onViewDocuments?: (event: EventResponse) => void
}

function payloadSnippet(payload: EventResponse['payload'], maxLen = 80): string {
  if (!payload || typeof payload !== 'object') return '—'
  const str = JSON.stringify(payload)
  return str.length <= maxLen ? str : str.slice(0, maxLen) + '…'
}

/** Groups events by date (event_time), sorted latest-first within each day. */
function groupEventsByDate(events: EventResponse[]): Map<string, EventResponse[]> {
  const sorted = [...events].sort(
    (a, b) => new Date(b.event_time).getTime() - new Date(a.event_time).getTime()
  )
  const map = new Map<string, EventResponse[]>()
  for (const event of sorted) {
    const dateKey = formatEventDate(event.event_time)
    const list = map.get(dateKey) ?? []
    list.push(event)
    map.set(dateKey, list)
  }
  return map
}

export function EventsTimeline({
  events,
  documentCounts = {},
  showSubjectColumn = false,
  subjectDisplayNames,
  onSelectEvent,
  selectedEventId,
  onViewDetails,
  onViewDocuments,
}: EventsTimelineProps) {
  const byDate = useMemo(() => groupEventsByDate(events), [events])

  if (events.length === 0) return null

  return (
    <div className="relative">
      {/* Vertical line: full height, positioned by the time column + node */}
      <div
        className="absolute left-[4.25rem] top-0 bottom-0 w-px bg-border"
        aria-hidden
      />
      <div className="space-y-0">
        {Array.from(byDate.entries()).map(([dateLabel, dayEvents]) => (
          <div key={dateLabel} className="space-y-0">
            {/* Date separator */}
            <div className="flex items-center gap-3 py-2 px-0">
              <div className="w-[4.25rem] shrink-0" />
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs font-medium text-muted-foreground tabular-nums shrink-0">
                {dateLabel}
              </span>
              <div className="h-px w-8 bg-border shrink-0" />
            </div>
            {/* Events for this day */}
            {dayEvents.map((event) => {
              const docCount = documentCounts[event.id] ?? 0
              const hasDocuments = docCount > 0
              const eventDate = new Date(event.event_time)
              const isSelected = selectedEventId === event.id

              return (
                <div
                  key={event.id}
                  role={onSelectEvent ? 'button' : undefined}
                  tabIndex={onSelectEvent ? 0 : undefined}
                  onClick={() => onSelectEvent?.(event)}
                  onKeyDown={(e) => {
                    if (onSelectEvent && (e.key === 'Enter' || e.key === ' ')) {
                      e.preventDefault()
                      onSelectEvent(event)
                    }
                  }}
                  className={cn(
                    'group relative flex gap-3 py-2 pl-0 pr-2 transition-colors cursor-default',
                    onSelectEvent && 'cursor-pointer',
                    'hover:bg-[var(--dashboard-accent-muted)]/30',
                    isSelected && 'bg-[var(--dashboard-accent-muted)]/50'
                  )}
                >
                  {/* Time + node column: line runs at right edge (4.25rem), node centered on it */}
                  <div className="flex w-[4.25rem] shrink-0 items-start pt-0.5">
                    <span className="text-xs text-muted-foreground tabular-nums">
                      {formatEventTimeWithSeconds(eventDate)}
                    </span>
                    <span
                      className={cn(
                        'absolute left-[4.25rem] top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-border bg-background shrink-0',
                        'group-hover:border-[var(--dashboard-accent)]',
                        isSelected && 'border-[var(--dashboard-accent)] bg-[var(--dashboard-accent-muted)]'
                      )}
                    />
                  </div>
                  {/* Content card — row click selects; buttons/links stop propagation */}
                  <div
                    className={cn(
                      'min-w-0 flex-1 rounded-none border py-2 px-3 text-sm transition-colors',
                      isSelected
                        ? 'border-[var(--dashboard-accent)]/60 bg-[var(--dashboard-accent-muted)]/30'
                        : 'border-border/60 bg-card/50'
                    )}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0 flex-1 space-y-0.5">
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                          <span className="font-medium text-foreground">
                            {event.event_type}
                          </span>
                          <span className="text-xs text-muted-foreground font-mono">
                            v{event.schema_version}
                          </span>
                          {showSubjectColumn && (
                            <Link
                              to="/subjects/$subjectId"
                              params={{ subjectId: event.subject_id }}
                              search={{ tab: 'events' }}
                              className="text-xs truncate text-muted-foreground hover:text-[var(--dashboard-accent)] transition-colors"
                              title={subjectDisplayNames?.[event.subject_id] ? event.subject_id : undefined}
                              onClick={(e) => e.stopPropagation()}
                            >
                              {subjectDisplayNames?.[event.subject_id] ?? event.subject_id}
                            </Link>
                          )}
                        </div>
                        <p
                          className="text-xs text-muted-foreground font-mono truncate"
                          title={JSON.stringify(event.payload)}
                        >
                          {payloadSnippet(event.payload)}
                        </p>
                      </div>
                      <div className="flex items-center gap-0.5 shrink-0">
                        {hasDocuments ? (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              onViewDocuments?.(event)
                            }}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded-none bg-[var(--dashboard-accent-muted)] text-[var(--dashboard-accent)] hover:opacity-90 text-xs font-medium tabular-nums transition-opacity"
                            title={`${docCount} document${docCount !== 1 ? 's' : ''}`}
                          >
                            <FileText className="w-3 h-3" strokeWidth={1.75} />
                            {docCount}
                          </button>
                        ) : (
                          <span className="text-muted-foreground/40 text-xs px-2">—</span>
                        )}
                        {onViewDetails && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              onViewDetails(event)
                            }}
                            className="p-2 rounded-none text-muted-foreground hover:text-[var(--dashboard-accent)] hover:bg-[var(--dashboard-accent-muted)]/50 transition-colors"
                            title="View details"
                            aria-label="View details"
                          >
                            <Eye className="w-4 h-4" strokeWidth={1.75} />
                          </button>
                        )}
                        <Link
                          to="/subjects/$subjectId/events/$eventId"
                          params={{ subjectId: event.subject_id, eventId: event.id }}
                          className="inline-flex items-center gap-1 px-2 py-1.5 rounded-none text-xs font-medium text-muted-foreground hover:text-[var(--dashboard-accent)] hover:bg-[var(--dashboard-accent-muted)]/50 transition-colors"
                          title="Open event"
                          onClick={(e) => e.stopPropagation()}
                        >
                          View
                          <ArrowUpRight className="w-3.5 h-3.5" strokeWidth={1.75} />
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}
