import { Link } from '@tanstack/react-router'
import { Check, CheckCircle, ChevronRight, Copy, FileText, Link2 } from 'lucide-react'
import { useState } from 'react'
import { formatEventDate, formatEventTime } from '@/lib/format-date'
import type { EventResponse } from '@/lib/types'

// Column definitions - single source of truth
const columns = [
  { key: 'block', label: '#', width: 'w-14', align: 'center' },
  { key: 'type', label: 'Event Type', width: 'w-[18%]', align: 'left' },
  { key: 'version', label: 'Version', width: 'w-16', align: 'center' },
  { key: 'date', label: 'Date', width: 'w-28', align: 'left' },
  { key: 'time', label: 'Time', width: 'w-20', align: 'left' },
  { key: 'hash', label: 'Hash', width: 'w-[18%]', align: 'left' },
  { key: 'prevHash', label: 'Prev Hash', width: 'w-[18%]', align: 'left' },
  { key: 'docs', label: 'Docs', width: 'w-14', align: 'center' },
  { key: 'action', label: '', width: 'w-16', align: 'center' },
] as const

const colStyles: Record<string, string> = Object.fromEntries(
  columns.map((col) => [col.key, `${col.width} text-${col.align}`]),
)

export interface EventBlockProps {
  event: EventResponse
  index: number
  isGenesis?: boolean
  documentCount?: number
  /** When set, row is clickable and calls this instead of navigating to event page (e.g. for drawer) */
  onEventClick?: (event: EventResponse) => void
}

function HashCell({
  hash,
  isLink,
  copiedHash,
  onCopy,
}: {
  hash: string | null | undefined
  isLink?: boolean
  copiedHash: string | null
  onCopy: (hash: string, e: React.MouseEvent) => void
}) {
  if (!hash) return <span className="text-muted-foreground">—</span>

  return (
    <div className="flex items-center gap-1.5 group/hash">
      {isLink && <Link2 className="w-3 h-3 text-muted-foreground/50 shrink-0" />}
      <code className="text-xs font-mono text-muted-foreground">{hash.slice(0, 16)}...</code>
      <button
        type="button"
        onClick={(e) => onCopy(hash, e)}
        className="opacity-0 group-hover/hash:opacity-100 transition-opacity p-0.5 hover:bg-muted rounded-none"
        title="Copy full hash"
      >
        {copiedHash === hash ? (
          <Check className="w-3 h-3 text-green-500" />
        ) : (
          <Copy className="w-3 h-3 text-muted-foreground" />
        )}
      </button>
    </div>
  )
}

function CellLink({
  to,
  params,
  className,
  children,
  onEventClick,
  event,
}: {
  to: string
  params: { subjectId: string; eventId: string }
  className?: string
  children: React.ReactNode
  onEventClick?: (event: EventResponse) => void
  event: EventResponse
}) {
  if (onEventClick) {
    return (
      <span
        role="button"
        tabIndex={0}
        onClick={(e) => {
          e.preventDefault()
          onEventClick(event)
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onEventClick(event)
          }
        }}
        className={className}
      >
        {children}
      </span>
    )
  }
  return (
    <Link to={to} params={params} className={className}>
      {children}
    </Link>
  )
}

export function EventBlockRow({
  event,
  index,
  isGenesis = false,
  documentCount = 0,
  onEventClick,
}: EventBlockProps) {
  const [copiedHash, setCopiedHash] = useState<string | null>(null)
  const linkParams = { subjectId: event.subject_id, eventId: event.id }

  const copyHash = (hash: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    navigator.clipboard.writeText(hash)
    setCopiedHash(hash)
    setTimeout(() => setCopiedHash(null), 1500)
  }

  const eventDate = new Date(event.event_time)
  const cell =
    'py-2.5 px-3 bg-card group-hover:bg-muted/30 border-y border-border/50 transition-colors'

  return (
    <tr className="group cursor-pointer">
      <td className={`${cell} ${colStyles.block} border-l rounded-none`}>
        <CellLink
          to="/subjects/$subjectId/events/$eventId"
          params={linkParams}
          onEventClick={onEventClick}
          event={event}
          className="flex items-center justify-center"
        >
          <div
            className={`w-7 h-7 rounded-none flex items-center justify-center ${
              isGenesis ? 'bg-primary/20 border-2 border-primary' : 'bg-muted border border-border'
            }`}
          >
            <span
              className={`font-semibold ${isGenesis ? 'text-[10px] text-primary' : 'text-xs text-muted-foreground'}`}
            >
              {isGenesis ? 'G' : index.toString().padStart(2, '0')}
            </span>
          </div>
        </CellLink>
      </td>

      <td className={`${cell} ${colStyles.type}`}>
        <CellLink
          to="/subjects/$subjectId/events/$eventId"
          params={linkParams}
          onEventClick={onEventClick}
          event={event}
          className="flex items-center gap-2"
        >
          <span className="font-medium text-sm text-foreground">{event.event_type}</span>
          {isGenesis && (
            <span className="px-1.5 py-0.5 text-[10px] font-medium bg-primary/10 text-primary rounded-none shrink-0">
              Genesis
            </span>
          )}
        </CellLink>
      </td>

      <td className={`${cell} ${colStyles.version}`}>
        <CellLink
          to="/subjects/$subjectId/events/$eventId"
          params={linkParams}
          onEventClick={onEventClick}
          event={event}
          className="block"
        >
          <span className="text-xs text-muted-foreground">v{event.schema_version}</span>
        </CellLink>
      </td>

      <td className={`${cell} ${colStyles.date} text-xs text-muted-foreground whitespace-nowrap`}>
        <CellLink
          to="/subjects/$subjectId/events/$eventId"
          params={linkParams}
          onEventClick={onEventClick}
          event={event}
          className="block"
        >
          {formatEventDate(eventDate)}
        </CellLink>
      </td>

      <td
        className={`${cell} ${colStyles.time} text-xs font-mono text-muted-foreground whitespace-nowrap`}
      >
        <CellLink
          to="/subjects/$subjectId/events/$eventId"
          params={linkParams}
          onEventClick={onEventClick}
          event={event}
          className="block"
        >
          {formatEventTime(eventDate)}
        </CellLink>
      </td>

      <td className={`${cell} ${colStyles.hash}`}>
        <HashCell hash={event.hash as string} copiedHash={copiedHash} onCopy={copyHash} />
      </td>

      <td className={`${cell} ${colStyles.prevHash}`}>
        {isGenesis ? (
          <CellLink
            to="/subjects/$subjectId/events/$eventId"
            params={linkParams}
            onEventClick={onEventClick}
            event={event}
            className="block"
          >
            <span className="text-xs text-muted-foreground">—</span>
          </CellLink>
        ) : (
          <HashCell
            hash={event.payload.previous_hash as string}
            isLink
            copiedHash={copiedHash}
            onCopy={copyHash}
          />
        )}
      </td>

      <td className={`${cell} ${colStyles.docs}`}>
        <CellLink
          to="/subjects/$subjectId/events/$eventId"
          params={linkParams}
          onEventClick={onEventClick}
          event={event}
          className="flex items-center justify-center"
        >
          {documentCount > 0 ? (
            <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium bg-blue-100 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 rounded-none">
              <FileText className="w-2.5 h-2.5" />
              {documentCount}
            </span>
          ) : (
            <span className="text-xs text-muted-foreground/50">—</span>
          )}
        </CellLink>
      </td>

      <td className={`${cell} ${colStyles.action} border-r rounded-none`}>
        <CellLink
          to="/subjects/$subjectId/events/$eventId"
          params={linkParams}
          onEventClick={onEventClick}
          event={event}
          className="flex items-center justify-center gap-1"
        >
          <CheckCircle className="w-4 h-4 text-green-500" />
          <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
        </CellLink>
      </td>
    </tr>
  )
}

export interface EventBlockChainProps {
  events: EventResponse[]
  documentCounts?: Record<string, number>
  /** Total number of events across all pages (for correct block numbering) */
  totalEvents?: number
  /** Current page offset (0-indexed, for correct block numbering) */
  pageOffset?: number
  /** When set, clicking an event calls this instead of navigating (e.g. open drawer) */
  onEventClick?: (event: EventResponse) => void
}

export function EventBlockChain({
  events,
  documentCounts = {},
  totalEvents,
  pageOffset = 0,
  onEventClick,
}: EventBlockChainProps) {
  if (events.length === 0) return null

  // Sort events by time (oldest first) to determine block indices
  const sortedByTime = [...events].sort(
    (a, b) => new Date(a.event_time).getTime() - new Date(b.event_time).getTime(),
  )

  // Calculate global block indices
  // If we have totalEvents, we're paginating newest-first, so calculate from the end
  // Otherwise fall back to local indexing
  const blockIndexMap = new Map<string, number>()

  if (totalEvents !== undefined && totalEvents > 0) {
    // Events are displayed newest-first, but block numbers should be oldest=0
    // Page 0 shows the newest events (indices: totalEvents-1 down to totalEvents-pageSize)
    // The oldest event on current page has index: totalEvents - pageOffset - events.length
    const oldestIndexOnPage = totalEvents - pageOffset - events.length

    sortedByTime.forEach((e, i) => {
      blockIndexMap.set(e.id, oldestIndexOnPage + i)
    })
  } else {
    // Fallback: local indexing when total is unknown
    sortedByTime.forEach((e, i) => {
      blockIndexMap.set(e.id, i)
    })
  }

  // Display latest first
  const displayEvents = [...events].sort(
    (a, b) => new Date(b.event_time).getTime() - new Date(a.event_time).getTime(),
  )

  return (
    <div className="space-y-1">
      {/* Header */}
      <div className="bg-muted/50 rounded-none border border-border">
        <table className="w-full table-fixed">
          <thead>
            <tr className="text-xs font-medium text-muted-foreground">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`py-2 px-3 font-medium ${col.width} text-${col.align}`}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
        </table>
      </div>

      {/* Rows */}
      <table className="w-full table-fixed border-separate" style={{ borderSpacing: '0 4px' }}>
        <tbody>
          {displayEvents.map((event) => {
            const blockIndex = blockIndexMap.get(event.id) ?? 0
            return (
              <EventBlockRow
                key={event.id}
                event={event}
                index={blockIndex}
                isGenesis={blockIndex === 0}
                documentCount={documentCounts[event.id] || 0}
                onEventClick={onEventClick}
              />
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
