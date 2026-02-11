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

export function useSubjects({ filterType, search }: UseSubjectsProps = {}) {
  const queryKey = ['subjects', { filterType, search }]

  const { data, error, isLoading, isError } = useQuery({
    queryKey,
    queryFn: async () => {
      const params: any = {}
      if (filterType) {
        params.subject_type = filterType
      }
      if (search) {
        params.q = search
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

            // Get event count and last event date from paginated response
            let eventCount = 0
            let lastEventDate: string | undefined

            if (eventsResponse && eventsResponse.total > 0) {
              eventCount = eventsResponse.total
              // Events are sorted by date descending, so first item is most recent
              if (eventsResponse.items.length > 0) {
                lastEventDate = eventsResponse.items[0].created_at
              }
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
