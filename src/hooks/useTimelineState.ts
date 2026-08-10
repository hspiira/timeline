import { useState } from 'react'

export function useTimelineState() {
  const [collapsedDates, setCollapsedDates] = useState<Set<string>>(new Set())
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set())
  const [hoveredEvent, setHoveredEvent] = useState<string | null>(null)

  const toggleDate = (date: string) => {
    setCollapsedDates(prev => {
      const next = new Set(prev)
      next.has(date) ? next.delete(date) : next.add(date)
      return next
    })
  }

  const toggleEvent = (eventId: string) => {
    setExpandedEvents(prev => {
      const next = new Set(prev)
      next.has(eventId) ? next.delete(eventId) : next.add(eventId)
      return next
    })
  }

  return {
    collapsedDates,
    expandedEvents,
    hoveredEvent,
    setHoveredEvent,
    toggleDate,
    toggleEvent
  }
}
