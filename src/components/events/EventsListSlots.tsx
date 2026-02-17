import { Loader2 } from 'lucide-react'
import { EVENTS_SEARCH_EMPTY_MESSAGE } from '@/lib/events'

/** Shown when client-side search has no matches. Single source for copy (DRY). */
export function EventsSearchEmptyMessage() {
  return (
    <div className="py-8 text-center text-sm text-muted-foreground">
      {EVENTS_SEARCH_EMPTY_MESSAGE}
    </div>
  )
}

export interface EventsLoadingSentinelProps {
  loading: boolean
  sentinelRef: React.RefObject<HTMLDivElement | null>
}

/** Sentinel for infinite scroll; shows spinner when loading more. */
export function EventsLoadingSentinel({ loading, sentinelRef }: EventsLoadingSentinelProps) {
  return (
    <div
      ref={sentinelRef}
      className="flex items-center justify-center py-2 min-h-[1rem]"
    >
      {loading && (
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      )}
    </div>
  )
}
