import { Calendar, User, Clock, FileText, Eye } from 'lucide-react'
import type { EventResponse } from '@/lib/types'
import { formatEventDateTime } from '@/lib/format-date'

export interface EventCardProps {
  event: EventResponse
  documentCount?: number
  onViewDetails?: () => void
  onViewDocuments?: () => void
}

export function EventCard({
  event,
  documentCount = 0,
  onViewDetails,
  onViewDocuments,
}: EventCardProps) {
  const hasDocuments = documentCount > 0

  return (
    <div className="bg-linear-to-r from-card to-card/50 backdrop-blur-sm rounded-none p-3 sm:p-4 border border-transparent hover:border-blue-200/60 dark:hover:border-blue-800/40 transition-colors shadow-sm hover:shadow-md">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 sm:gap-2.5 flex-1 min-w-0">
          {/* Event Icon */}
          <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-none bg-linear-to-br from-blue-500 to-blue-600 flex items-center justify-center shrink-0">
            <Calendar className="w-3 h-3 sm:w-4 sm:h-4 text-white" />
          </div>

          {/* Event Details */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1 sm:gap-1.5 mb-2 flex-wrap">
              <h3 className="font-semibold text-foreground text-xs sm:text-sm truncate">
                {event.event_type}
              </h3>
              <span className="px-1.5 sm:px-2 py-0.5 text-xs font-mono bg-slate-700 dark:bg-slate-600 text-slate-100 dark:text-slate-200 rounded-none shrink-0">
                {event.id.slice(0, 8)}
              </span>

              {/* Document Count and View Details - Same Row */}
              {hasDocuments && (
                <button
                  onClick={onViewDocuments}
                  className="inline-flex items-center gap-0.5 sm:gap-1 px-1.5 sm:px-2 py-0.5 bg-blue-100 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 rounded-none hover:bg-blue-200 dark:hover:bg-blue-900/40 transition-colors text-xs shrink-0"
                  title={`${documentCount} document${documentCount !== 1 ? 's' : ''}`}
                >
                  <FileText className="w-2.5 h-2.5 sm:w-3 sm:h-3" />
                  <span className="font-medium">{documentCount}</span>
                </button>
              )}
              {onViewDetails && (
                <button
                  onClick={onViewDetails}
                  className="px-1.5 sm:px-2 py-0.5 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-950/30 rounded-none transition-colors shrink-0"
                  title="View details"
                >
                  <Eye className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                </button>
              )}
            </div>

            <div className="flex flex-col sm:flex-row sm:flex-wrap items-start sm:items-center gap-1 sm:gap-2 text-xs sm:text-sm text-muted-foreground mb-2">
              <div className="flex items-center gap-1">
                <User className="w-3 h-3 shrink-0" />
                <span className="truncate">Subject: {event.subject_id.slice(0, 8)}</span>
              </div>
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3 shrink-0" />
                <span className="truncate">{formatEventDateTime(event.event_time)}</span>
              </div>
            </div>

            {/* Payload Preview */}  
            {event.payload && (  
              <div className="mt-2 p-2 bg-slate-50 dark:bg-slate-900/50 rounded-none border border-slate-200 dark:border-slate-700 overflow-x-auto">  
                <pre className="text-xs text-foreground/90 whitespace-pre-wrap wrap-break-word max-h-32 overflow-y-auto">  
                  {(() => {  
                    const str = JSON.stringify(event.payload, null, 2)  
                    return str.length > 500 ? str.slice(0, 500) + '\n...' : str  
                  })()}  
                </pre>  
              </div>  
            )} 
          </div>
        </div>
      </div>
    </div>
  )
}
