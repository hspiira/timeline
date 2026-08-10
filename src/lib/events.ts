import type { EventResponse } from '@/lib/types'

/** Find an event by id in a list. Single place for lookup logic (DRY). */
export function findEventById(
  events: EventResponse[],
  id: string | null
): EventResponse | undefined {
  if (!id) return undefined
  return events.find((e) => e.id === id)
}

/** Message shown when client-side search has no matches. */
export const EVENTS_SEARCH_EMPTY_MESSAGE =
  'No events match your search. Try a different term or clear the search.'
