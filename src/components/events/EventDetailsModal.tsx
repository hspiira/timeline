import { Clock, Code, Eye, FileText, User, X } from 'lucide-react'
import { useState } from 'react'
import { Modal } from '@/components/ui/Modal'
import { DocumentList } from '@/components/documents/DocumentList'
import type { EventResponse } from '@/lib/types'

export interface EventDetailsModalProps {
  event: EventResponse
  onClose: () => void
}

type ViewMode = 'modern' | 'json'

export function EventDetailsModal({ event, onClose }: EventDetailsModalProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('modern')
  return (
    <Modal isOpen={true} onClose={onClose} maxWidth="max-w-3xl" closeButton={false}>
      {/* Custom Header with gradient background */}
      <div className="flex items-center justify-between mb-4 pb-4 border-b border-blue-200 dark:border-blue-900 bg-linear-to-r from-blue-50 to-blue-100/50 dark:from-blue-950/30 dark:to-blue-900/20 -mx-4 sm:-mx-6 -mt-4 sm:-mt-6 px-4 sm:px-6 pt-4 sm:pt-6 rounded-t-xs">
        <div>
          <h2 className="font-semibold text-foreground text-lg">{event.event_type}</h2>
          <p className="text-xs text-muted-foreground mt-1">Event ID: {event.id}</p>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 hover:bg-muted rounded-none transition-colors font-medium"
          title="Close"
          aria-label="Close modal"
        >
          <X className="w-4 h-4 text-muted-foreground" />
        </button>
      </div>

      {/* Content */}
      <div className="space-y-4">
          {/* Event Metadata */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-muted/50 rounded-none border border-border/50">
              <div className="flex items-center gap-2 mb-1">
                <User className="w-4 h-4 text-muted-foreground" />
                <span className="text-xs font-medium text-muted-foreground">Subject ID</span>
              </div>
              <p className="text-sm font-mono text-foreground">{event.subject_id}</p>
            </div>

            <div className="p-3 bg-muted/50 rounded-none border border-border/50">
              <div className="flex items-center gap-2 mb-1">
                <Clock className="w-4 h-4 text-muted-foreground" />
                <span className="text-xs font-medium text-muted-foreground">Event Time</span>
              </div>
              <p className="text-sm text-foreground">
                {new Date(event.event_time).toLocaleString()}
              </p>
            </div>
          </div>

          {/* Payload */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold">Event Data</h3>
              <div className="flex gap-1">
                <button
                  type="button"
                  onClick={() => setViewMode('modern')}
                  className={`flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-none transition-colors ${
                    viewMode === 'modern'
                      ? 'bg-blue-100 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
                      : 'text-muted-foreground hover:bg-muted border border-transparent hover:border-border/50'
                  }`}
                  title="Modern view"
                >
                  <Eye className="w-3.5 h-3.5" />
                  Modern
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('json')}
                  className={`flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-none transition-colors ${
                    viewMode === 'json'
                      ? 'bg-blue-100 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
                      : 'text-muted-foreground hover:bg-muted border border-transparent hover:border-border/50'
                  }`}
                  title="JSON view"
                >
                  <Code className="w-3.5 h-3.5" />
                  JSON
                </button>
              </div>
            </div>

            {viewMode === 'modern' && event.payload && (
              <div className="bg-slate-50 dark:bg-slate-900/30 rounded-none border border-slate-200 dark:border-slate-700 p-3">
                <div className="space-y-2">
                  {Object.entries(event.payload).map(([key, value]) => {
                    const displayValue = (() => {
                      if (value === null) return <span className="text-muted-foreground italic">null</span>
                      if (value === undefined) return <span className="text-muted-foreground italic">undefined</span>
                      if (typeof value === 'boolean') {
                        return (
                          <span className={value ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}>
                            {value ? 'true' : 'false'}
                          </span>
                        )
                      }
                      if (typeof value === 'number') {
                        return <span className="text-blue-600 dark:text-blue-400">{value}</span>
                      }
                      if (typeof value === 'object') {
                        return <span className="text-slate-600 dark:text-slate-300 font-mono text-xs">{JSON.stringify(value)}</span>
                      }
                      return <span className="text-foreground">{String(value)}</span>
                    })()

                    return (
                      <div key={key} className="flex gap-2">
                        <span className="font-medium text-slate-600 dark:text-slate-400 text-sm min-w-fit">{key}:</span>
                        <span className="text-foreground text-sm wrap-break-word">{displayValue}</span>
                      </div>
                    )
                  })}
                </div>
                {Object.keys(event.payload).length === 0 && (
                  <p className="text-xs text-muted-foreground italic">No data</p>
                )}
              </div>
            )}

            {viewMode === 'json' && event.payload && (
              <div className="bg-slate-50 dark:bg-slate-900/50 rounded-none border border-slate-200 dark:border-slate-700 p-3">
                <pre className="text-xs text-foreground/90 overflow-x-auto">
                  {JSON.stringify(event.payload, null, 2)}
                </pre>
              </div>
            )}

            {!event.payload && (
              <div className="bg-slate-50 dark:bg-slate-900/30 rounded-none border border-slate-200 dark:border-slate-700 p-3">
                <p className="text-xs text-muted-foreground italic">No payload data</p>
              </div>
            )}
          </div>

        {/* Documents */}
        <div>
          <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Linked Documents
          </h3>
          <DocumentList eventId={event.id} readOnly={true} />
        </div>
      </div>
    </Modal>
  )
}
