import { FileText } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { LoadingIcon } from '@/components/ui/icons'
import { timelineApi } from '@/lib/api-client'
import { formatEventTime } from '@/lib/format-date'
import type { EventResponse } from '@/lib/types'

interface TimelineEventProps {
  event: EventResponse
  isExpanded: boolean
  isHovered: boolean
  onToggle: () => void
  onHover: (eventId: string | null) => void
  onViewDocuments?: (eventId: string) => void
}

export function TimelineEvent({
  event,
  isExpanded,
  isHovered,
  onToggle,
  onHover,
  onViewDocuments,
}: TimelineEventProps) {
  const [documentCount, setDocumentCount] = useState<number | null>(null)
  const [loadingDocuments, setLoadingDocuments] = useState(false)
  const showPayload = isExpanded || isHovered

  const checkDocuments = useCallback(async () => {
    if (documentCount !== null) return // Already fetched
    setLoadingDocuments(true)
    try {
      const { data, error } = await timelineApi.documents.listByEvent(event.id)
      if (!error && data && Array.isArray(data)) {
        setDocumentCount(data.length)
      }
    } catch (err) {
      console.error('Failed to load document count:', err)
    } finally {
      setLoadingDocuments(false)
    }
  }, [documentCount, event.id])

  // Load document count when event is visible
  useEffect(() => {
    if (isExpanded || isHovered) {
      checkDocuments()
    }
  }, [isExpanded, isHovered, checkDocuments])

  const hasDocuments = documentCount !== null && documentCount > 0

  return (
    <div className="flex gap-4">
      <div className="flex flex-col items-center pt-1">
        <div className="w-2 h-2 rounded-none bg-foreground/60" />
      </div>

      <div className="flex-1">
        <div
          onClick={onToggle}
          onMouseEnter={() => {
            onHover(event.id)
            checkDocuments()
          }}
          onMouseLeave={() => onHover(null)}
          className="flex justify-between hover:bg-blue-50/50 dark:hover:bg-blue-950/20 px-2 py-1.5 rounded-none cursor-pointer transition-colors"
        >
          <div className="flex gap-2 items-center">
            <span className="text-xs text-muted-foreground font-mono">
              {formatEventTime(event.event_time)}
            </span>
            <span className="font-mono text-xs bg-linear-to-r from-slate-600 to-slate-700 dark:from-slate-700 dark:to-slate-800 text-slate-100 px-2 py-0.5 rounded-none">
              {event.subject_id.slice(0, 8)}
            </span>
            <span className="text-sm font-semibold text-blue-700 dark:text-blue-300">
              {event.event_type}
            </span>

            {/* Document Indicator */}
            {loadingDocuments && (
              <div className="text-xs text-muted-foreground">
                <LoadingIcon size="sm" className="inline" />
              </div>
            )}
            {hasDocuments && !loadingDocuments && (
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation()
                  onViewDocuments?.(event.id)
                }}
                className="inline-flex items-center gap-1 px-2 py-0.5 h-auto bg-blue-100 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/40"
                title={`${documentCount} document${documentCount !== 1 ? 's' : ''}`}
              >
                <FileText className="w-3 h-3" />
                <span className="text-xs font-medium">{documentCount}</span>
              </Button>
            )}
          </div>
        </div>

        {showPayload && event.payload && (
          <div className="ml-2 mt-1 text-xs text-muted-foreground">
            {Object.entries(event.payload).map(([k, v]) => (
              <div key={k}>
                <strong>{k}:</strong> {String(v)}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
