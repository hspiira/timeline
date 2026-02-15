import { useQuery } from '@tanstack/react-query'
import { timelineApi } from '@/lib/api-client'
import { getApiErrorMessage } from '@/lib/api-utils'
import type { SubjectResponse } from '@/lib/types'

interface UseSubjectsProps {
  filterType?: string
  search?: string
}

export interface SubjectWithMetadata extends SubjectResponse {
  eventCount: number
  lastEventDate?: string
}

export function useSubjects({ filterType, search: _search }: UseSubjectsProps = {}) {
  // search is accepted for API compatibility but not sent to GET /subjects (no q param).
  // Use GET /search when implementing global/subject search in a later phase.
  const queryKey = ['subjects', { filterType }]

  const { data, error, isLoading, isError } = useQuery({
    queryKey,
    queryFn: async () => {
      // Backend GET /subjects does not support `q`; use subject_type filter only.
      // Global search will use GET /search in a later phase.
      const params: Parameters<typeof timelineApi.subjects.list>[0] = {}
      if (filterType) {
        params.subject_type = filterType
      }

      const { data, error: apiError } = await timelineApi.subjects.list(params)

      if (apiError) {
        throw new Error(getApiErrorMessage(apiError))
      }

      if (!data) {
        return []
      }

      // Fetch event counts for each subject in parallel
      const subjectsWithMetadata = await Promise.all(
        data.map(async (subject: SubjectResponse): Promise<SubjectWithMetadata> => {
          try {
            const { data: eventsResponse } = await timelineApi.events.list(subject.id)

            // events.list returns a flat array of EventListResponse
            let eventCount = 0
            let lastEventDate: string | undefined

            if (eventsResponse && eventsResponse.length > 0) {
              eventCount = eventsResponse.length
              // Events are sorted by date descending, so first item is most recent
              lastEventDate = eventsResponse[0].event_time
            }

            return {
              ...subject,
              eventCount,
              lastEventDate,
            }
          } catch {
            // If fetching events fails, just return subject with 0 count
            return {
              ...subject,
              eventCount: 0,
            }
          }
        })
      )

      return subjectsWithMetadata
    },
  })

  return {
    subjects: data ?? [],
    isLoading,
    isError,
    error: error as Error | null,
  }
}
