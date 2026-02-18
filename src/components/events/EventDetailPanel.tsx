import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import {
  CalendarPlus,
  Clock,
  Code,
  Eye,
  FileText,
  User,
  UserPlus,
  X,
  ArrowUpRight,
} from 'lucide-react'
import { DocumentList } from '@/components/documents/DocumentList'
import { formatDateTimeSafe, formatFullDateTime } from '@/lib/format-date'
import type { EventResponse } from '@/lib/types'
import { PayloadModernView } from './PayloadModernView'
import { cn } from '@/lib/utils'

export interface EventDetailPanelProps {
  event: EventResponse
  onClose: () => void
  className?: string
}

type PayloadViewMode = 'modern' | 'json'

type EventWithAudit = EventResponse & { created_by?: string | null; created_at?: string | null }

export function EventDetailPanel({ event, onClose, className }: EventDetailPanelProps) {
  const [payloadView, setPayloadView] = useState<PayloadViewMode>('modern')
  const [documentCount, setDocumentCount] = useState<number | null>(null)
  const ev = event as EventWithAudit
  const hasCreatedBy = ev.created_by != null && ev.created_by !== ''

  return (
    <aside
      className={cn(
        'flex flex-col h-full min-h-0 border-l border-border/60 bg-card/80',
        className
      )}
      aria-label="Event details"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 shrink-0 px-4 py-3 border-b border-border/60 bg-muted/20">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-foreground truncate">
            {event.event_type}
          </h3>
          <p className="text-xs text-muted-foreground font-mono truncate mt-0.5" title={event.id}>
            {event.id}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="shrink-0 p-2 rounded-none text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          title="Close"
          aria-label="Close panel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {/* Metadata */}
        <div className="grid grid-cols-1 gap-2">
          <div className="p-2.5 bg-muted/40 rounded-none border border-border/50">
            <div className="flex items-center gap-1.5 mb-0.5">
              <User className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
              <span className="text-xs font-medium text-muted-foreground">Subject</span>
            </div>
            <Link
              to="/subjects/$subjectId"
              params={{ subjectId: event.subject_id }}
              search={{ tab: 'events' }}
              className="text-sm font-mono text-[var(--dashboard-accent)] hover:underline break-all"
            >
              {event.subject_id}
            </Link>
          </div>
          <div className="p-2.5 bg-muted/40 rounded-none border border-border/50">
            <div className="flex items-center gap-1.5 mb-0.5">
              <Clock className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
              <span className="text-xs font-medium text-muted-foreground">Event time</span>
            </div>
            <p className="text-sm text-foreground tabular-nums">
              {formatFullDateTime(event.event_time)}
            </p>
          </div>
          {hasCreatedBy && (
            <div className="p-2.5 bg-muted/40 rounded-none border border-border/50">
              <div className="flex items-center gap-1.5 mb-0.5">
                <UserPlus className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                <span className="text-xs font-medium text-muted-foreground">Created by</span>
              </div>
              <p className="text-sm text-foreground">{ev.created_by}</p>
            </div>
          )}
          <div className="p-2.5 bg-muted/40 rounded-none border border-border/50">
            <div className="flex items-center gap-1.5 mb-0.5">
              <CalendarPlus className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
              <span className="text-xs font-medium text-muted-foreground">Record created</span>
            </div>
            <p className="text-sm text-foreground tabular-nums">
              {formatDateTimeSafe(ev.created_at)}
            </p>
          </div>
        </div>

        {/* Payload */}
        <div>
          <div className="flex items-center justify-between gap-2 mb-2">
            <h4 className="text-xs font-semibold text-foreground">
              Event data
            </h4>
            <div className="flex gap-0.5">
              <button
                type="button"
                onClick={() => setPayloadView('modern')}
                className={cn(
                  'flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-none transition-colors',
                  payloadView === 'modern'
                    ? 'bg-primary/10 text-primary border border-primary/20'
                    : 'text-muted-foreground hover:bg-muted border border-transparent'
                )}
              >
                <Eye className="w-3 h-3" />
                Modern
              </button>
              <button
                type="button"
                onClick={() => setPayloadView('json')}
                className={cn(
                  'flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-none transition-colors',
                  payloadView === 'json'
                    ? 'bg-primary/10 text-primary border border-primary/20'
                    : 'text-muted-foreground hover:bg-muted border border-transparent'
                )}
              >
                <Code className="w-3 h-3" />
                JSON
              </button>
            </div>
          </div>
          {payloadView === 'modern' && event.payload && (
            <div className="bg-muted/30 rounded-none border border-border/50 p-2.5">
              <PayloadModernView payload={event.payload} />
            </div>
          )}
          {payloadView === 'json' && event.payload && (
            <div className="bg-muted/30 rounded-none border border-border/50 p-2.5 overflow-x-auto">
              <pre className="text-xs text-foreground/90 whitespace-pre">
                {JSON.stringify(event.payload, null, 2)}
              </pre>
            </div>
          )}
          {!event.payload && (
            <div className="bg-muted/30 rounded-none border border-border/50 p-2.5">
              <p className="text-xs text-muted-foreground italic">No payload data</p>
            </div>
          )}
        </div>

        {/* Documents */}
        <div>
          <h4 className="text-xs font-semibold text-foreground mb-2 flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5" />
            Linked documents {documentCount != null && `(${documentCount})`}
          </h4>
          <DocumentList
            eventId={event.id}
            readOnly={true}
            onDocumentsLoaded={setDocumentCount}
          />
        </div>

        {/* Open full page */}
        <div className="pt-2 border-t border-border/50">
          <Link
            to="/subjects/$subjectId/events/$eventId"
            params={{ subjectId: event.subject_id, eventId: event.id }}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--dashboard-accent)] hover:underline"
          >
            Open event page
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </aside>
  )
}
