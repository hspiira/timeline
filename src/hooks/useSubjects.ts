import { useQuery } from '@tanstack/react-query'
import { timelineApi } from '@/lib/api-client'
import { getApiErrorMessage } from '@/lib/api-utils'
import type { SubjectResponse } from '@/lib/types'

interface UseSubjectsProps {
  filterType?: string
  search?: string
}

export type IntegrityStatus = 'valid' | 'broken' | 'unknown'

export interface SubjectWithMetadata extends SubjectResponse {
  eventCount: number
  lastEventDate?: string
  /** Chain integrity status from verify API; undefined until fetched */
  integrityStatus?: IntegrityStatus
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

      // Integrity from list when backend adds chain_status to GET /subjects response; until then from verify API per subject.
      // Fetch event counts and integrity status per subject in parallel
      const subjectsWithMetadata = await Promise.all(
        data.map(async (subject: SubjectResponse): Promise<SubjectWithMetadata> => {
          const [eventsResult, verifyResult] = await Promise.all([
            timelineApi.events.list(subject.id),
            timelineApi.integrity
              .verifySubject(subject.id)
              .catch(() => ({ data: null, error: true })),
          ])

          let eventCount = 0
          let lastEventDate: string | undefined
          if (eventsResult.data && eventsResult.data.length > 0) {
            eventCount = eventsResult.data.length
            lastEventDate = eventsResult.data[0].event_time
          }

          let integrityStatus: SubjectWithMetadata['integrityStatus'] = 'unknown'
          if (!verifyResult.error && verifyResult.data && 'is_chain_valid' in verifyResult.data) {
            integrityStatus = (verifyResult.data as { is_chain_valid: boolean }).is_chain_valid
              ? 'valid'
              : 'broken'
          }

          return {
            ...subject,
            eventCount,
            lastEventDate,
            integrityStatus,
          }
        }),
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
