import { Link } from '@tanstack/react-router'
import { ArrowUpRight, Eye, FileText } from 'lucide-react'
import { formatEventDate, formatEventTime } from '@/lib/format-date'
import type { EventResponse } from '@/lib/types'

export interface EventsTableProps {
  events: EventResponse[]
  documentCounts?: Record<string, number>
  /** When true, shows a Subject column. Pass subjectDisplayNames to show display names instead of ids. */
  showSubjectColumn?: boolean
  /** Map of subject_id -> display_name for the Subject column. Falls back to subject_id when missing. */
  subjectDisplayNames?: Record<string, string>
  onViewDetails?: (event: EventResponse) => void
  onViewDocuments?: (event: EventResponse) => void
}

function payloadSnippet(payload: EventResponse['payload'], maxLen = 80): string {
  if (!payload || typeof payload !== 'object') return '—'
  const str = JSON.stringify(payload)
  return str.length <= maxLen ? str : `${str.slice(0, maxLen)}…`
}

export function EventsTable({
  events,
  documentCounts = {},
  showSubjectColumn = false,
  subjectDisplayNames,
  onViewDetails,
  onViewDocuments,
}: EventsTableProps) {
  if (events.length === 0) return null

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse">
        <thead>
          <tr className="border-b border-border/60">
            <th className="py-2 px-4 text-left font-display text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Date & time
            </th>
            <th className="py-2 px-4 text-left font-display text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Type
            </th>
            {showSubjectColumn && (
              <th className="py-2 px-4 text-left font-display text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Subject
              </th>
            )}
            <th className="py-2 px-4 text-left font-display text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Payload
            </th>
            <th className="py-2 px-4 text-center w-14 font-display text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Docs
            </th>
            <th className="py-2 pl-4 pr-4 text-right w-28" aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {events.map((event) => {
            const docCount = documentCounts[event.id] ?? 0
            const hasDocuments = docCount > 0
            const eventDate = new Date(event.event_time)

            return (
              <tr
                key={event.id}
                className="group text-sm border-b border-border/40 last:border-b-0 transition-colors hover:bg-[var(--dashboard-accent-muted)]/50"
              >
                <td className="py-2 px-4 text-muted-foreground whitespace-nowrap tabular-nums">
                  {formatEventDate(eventDate)} {formatEventTime(eventDate)}
                </td>
                <td className="py-2 px-4">
                  <span className="font-medium text-foreground">{event.event_type}</span>
                  <span className="ml-1.5 text-xs text-muted-foreground font-mono">
                    v{event.schema_version}
                  </span>
                </td>
                {showSubjectColumn && (
                  <td className="py-2 px-4 max-w-[180px]">
                    <Link
                      to="/subjects/$subjectId"
                      params={{ subjectId: event.subject_id }}
                      search={{ tab: 'events', event_id: undefined }}
                      className="text-sm truncate block text-muted-foreground hover:text-[var(--dashboard-accent)] transition-colors"
                      title={subjectDisplayNames?.[event.subject_id] ? event.subject_id : undefined}
                    >
                      {subjectDisplayNames?.[event.subject_id] ?? event.subject_id}
                    </Link>
                  </td>
                )}
                <td className="py-2 px-4 max-w-[220px]">
                  <span
                    className="text-muted-foreground text-xs truncate block font-mono"
                    title={JSON.stringify(event.payload)}
                  >
                    {payloadSnippet(event.payload)}
                  </span>
                </td>
                <td className="py-2 px-4 text-center">
                  {hasDocuments ? (
                    <button
                      type="button"
                      onClick={() => onViewDocuments?.(event)}
                      className="inline-flex items-center gap-1 px-2 py-1 rounded-none bg-[var(--dashboard-accent-muted)] text-[var(--dashboard-accent)] hover:opacity-90 text-xs font-medium tabular-nums transition-opacity"
                      title={`${docCount} document${docCount !== 1 ? 's' : ''}`}
                    >
                      <FileText className="w-3 h-3" strokeWidth={1.75} />
                      {docCount}
                    </button>
                  ) : (
                    <span className="text-muted-foreground/40 text-xs">—</span>
                  )}
                </td>
                <td className="py-2 pl-4 pr-4 text-right">
                  <div className="flex items-center justify-end gap-0.5">
                    {onViewDetails && (
                      <button
                        type="button"
                        onClick={() => onViewDetails(event)}
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
                    >
                      View
                      <ArrowUpRight className="w-3.5 h-3.5" strokeWidth={1.75} />
                    </Link>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
