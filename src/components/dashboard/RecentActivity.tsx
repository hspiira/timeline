import { Calendar, ChevronDown, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { EventDocumentsModal } from '@/components/documents/EventDocumentsModal'
import type { EventResponse } from '@/lib/types'
import { TimelineEvent } from './TimelineEvent'

interface RecentActivityProps {
  eventsByDate: Record<string, EventResponse[]>
  timeline: {
    collapsedDates: Set<string>
    expandedEvents: Set<string>
    hoveredEvent: string | null
    toggleDate: (date: string) => void
    toggleEvent: (eventId: string) => void
    setHoveredEvent: (eventId: string | null) => void
  }
}

export function RecentActivity({ eventsByDate, timeline }: RecentActivityProps) {
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const hasEvents = Object.keys(eventsByDate).length > 0

  const selectedEvent = selectedEventId
    ? Object.values(eventsByDate)
        .flat()
        .find((e) => e.id === selectedEventId)
    : null

  if (!hasEvents) {
    return (
      <div className="bg-card/80 backdrop-blur-sm rounded-none p-12 border border-border/50 text-center">
        <Calendar className="w-12 h-12 text-muted-foreground/50 mx-auto mb-3" />
        <h3 className="text-lg font-semibold text-foreground mb-2">No recent activity</h3>
        <p className="text-muted-foreground">Events will appear here as they occur</p>
      </div>
    )
  }
  return (
    <div className="space-y-6">
      {Object.entries(eventsByDate).map(([date, events]) => {
        const collapsed = timeline.collapsedDates.has(date)

        return (
          <div key={date}>
            <button
              type="button"
              onClick={() => timeline.toggleDate(date)}
              className="flex items-center gap-2 mb-4"
            >
              {collapsed ? <ChevronRight /> : <ChevronDown />}
              <span className="font-semibold">{date}</span>
              <span className="text-xs text-muted-foreground">({events.length})</span>
            </button>

            {!collapsed && (
              <div className="ml-6 space-y-3 max-h-96 overflow-y-auto">
                {events.map((event) => (
                  <TimelineEvent
                    key={event.id}
                    event={event}
                    isExpanded={timeline.expandedEvents.has(event.id)}
                    isHovered={timeline.hoveredEvent === event.id}
                    onToggle={() => timeline.toggleEvent(event.id)}
                    onHover={timeline.setHoveredEvent}
                    onViewDocuments={setSelectedEventId}
                  />
                ))}
              </div>
            )}
          </div>
        )
      })}

      {/* Documents Modal */}
      {selectedEvent && (
        <EventDocumentsModal
          eventId={selectedEvent.id}
          subjectId={selectedEvent.subject_id}
          eventType={selectedEvent.event_type}
          onClose={() => setSelectedEventId(null)}
          onDocumentsUpdated={() => {
            // Refresh document count by resetting selection
            setSelectedEventId(null)
          }}
        />
      )}
    </div>
  )
}
