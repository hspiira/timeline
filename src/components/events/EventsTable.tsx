import { Link } from '@tanstack/react-router'
import { FileText, Eye } from 'lucide-react'
import type { EventResponse } from '@/lib/types'
import { formatEventDate, formatEventTime } from '@/lib/format-date'

export interface EventsTableProps {
  events: EventResponse[]
  documentCounts?: Record<string, number>
  showSubjectColumn?: boolean
  onViewDetails?: (event: EventResponse) => void
  onViewDocuments?: (event: EventResponse) => void
}

function payloadSnippet(payload: EventResponse['payload'], maxLen = 80): string {
  if (!payload || typeof payload !== 'object') return '—'
  const str = JSON.stringify(payload)
  return str.length <= maxLen ? str : str.slice(0, maxLen) + '…'
}

export function EventsTable({
  events,
  documentCounts = {},
  showSubjectColumn = false,
  onViewDetails,
  onViewDocuments,
}: EventsTableProps) {
  if (events.length === 0) return null

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse">
        <thead>
          <tr className="text-left text-xs font-medium text-muted-foreground">
            <th className="py-2.5 pr-4">Date & time</th>
            <th className="py-2.5 pr-4">Type</th>
            {showSubjectColumn && (
              <th className="py-2.5 pr-4">Subject</th>
            )}
            <th className="py-2.5 pr-4">Payload</th>
            <th className="py-2.5 pr-4 text-center w-14">Docs</th>
            <th className="py-2.5 pl-4 text-right w-24"></th>
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
                className="group text-sm border-0 border-none hover:bg-muted/40 transition-colors"
              >
                <td className="py-2.5 pr-4 text-muted-foreground whitespace-nowrap">
                  {formatEventDate(eventDate)} {formatEventTime(eventDate)}
                </td>
                <td className="py-2.5 pr-4">
                  <span className="font-medium text-foreground">{event.event_type}</span>
                  <span className="ml-1.5 text-xs text-muted-foreground font-mono">
                    v{event.schema_version}
                  </span>
                </td>
                {showSubjectColumn && (
                  <td className="py-2.5 pr-4">
                    <Link
                      to="/subjects/$subjectId"
                      params={{ subjectId: event.subject_id }}
                      search={{ tab: 'events' }}
                      className="text-muted-foreground hover:text-foreground font-mono text-xs truncate max-w-[120px] inline-block"
                    >
                      {event.subject_id}
                    </Link>
                  </td>
                )}
                <td className="py-2.5 pr-4 max-w-[200px]">
                  <span className="text-muted-foreground text-xs truncate block" title={JSON.stringify(event.payload)}>
                    {payloadSnippet(event.payload)}
                  </span>
                </td>
                <td className="py-2.5 pr-4 text-center">
                  {hasDocuments ? (
                    <button
                      type="button"
                      onClick={() => onViewDocuments?.(event)}
                      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-none bg-muted/80 hover:bg-muted text-muted-foreground hover:text-foreground text-xs"
                      title={`${docCount} document${docCount !== 1 ? 's' : ''}`}
                    >
                      <FileText className="w-3 h-3" />
                      {docCount}
                    </button>
                  ) : (
                    <span className="text-muted-foreground/50 text-xs">—</span>
                  )}
                </td>
                <td className="py-2.5 pl-4 text-right">
                  <div className="flex items-center justify-end gap-1">
                    {onViewDetails && (
                      <button
                        type="button"
                        onClick={() => onViewDetails(event)}
                        className="p-1.5 rounded-none text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                        title="View details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    )}
                    <Link
                      to="/subjects/$subjectId/events/$eventId"
                      params={{ subjectId: event.subject_id, eventId: event.id }}
                      className="p-1.5 rounded-none text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                      title="Open event"
                    >
                      View
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
