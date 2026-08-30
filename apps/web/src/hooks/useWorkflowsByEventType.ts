import { useQuery } from '@tanstack/react-query'
import { timelineApi } from '@/lib/api-client'
import type { WorkflowResponse } from '@/lib/types'

export const WORKFLOWS_QUERY_KEY = ['workflows'] as const

/**
 * Fetches workflows and returns those triggered by the given event type.
 * Shares the same cache as other workflow list usage (dashboard, settings).
 */
export function useWorkflowsByEventType(eventType: string | undefined) {
  const {
    data: workflows = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: WORKFLOWS_QUERY_KEY,
    queryFn: async () => {
      const result = await timelineApi.workflows.list()
      if (result.error || !result.data) return []
      return result.data as WorkflowResponse[]
    },
    enabled: !!eventType,
  })

  const byEventType: WorkflowResponse[] =
    eventType == null || eventType === ''
      ? []
      : workflows.filter((w) => (w as WorkflowResponse).trigger_event_type === eventType)

  return {
    workflows: byEventType,
    allWorkflows: workflows,
    isLoading,
    error: error ?? null,
  }
}
