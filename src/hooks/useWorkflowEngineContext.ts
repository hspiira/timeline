/**
 * Workflow Engine Context – single source for entity lists used by the workflow builder.
 * Consumed by create/edit modals and NodeConfigPanel. Keeps entity fetching in one place (DRY).
 */

import { useEffect, useMemo, useState } from 'react'
import { useEventTypes } from '@/hooks/useEventTypes'
import { timelineApi } from '@/lib/api-client'
import { getApiErrorMessage } from '@/lib/api-utils'

export interface EventTransitionRuleRef {
  event_type: string
  required_prior_event_types: string[]
}

export interface SubjectTypeRef {
  id: string
  type_name: string
  display_name?: string | null
}

export interface RelationshipKindRef {
  id: string
  kind: string
  display_name?: string | null
}

export interface EventSchemaRef {
  event_type: string
  version?: number
  schema_id?: string
}

export interface WorkflowEngineContextValue {
  /** Event types from schemas (with fallback to events). */
  eventTypes: string[]
  /** Subject types for subject selectors and filters. */
  subjectTypes: SubjectTypeRef[]
  /** Event schemas list (for validation/hints). */
  eventSchemas: EventSchemaRef[]
  /** Transition rules: event_type -> required prior event types. */
  transitionRules: EventTransitionRuleRef[]
  /** Relationship kinds for create_relationship or relationship-based nodes. */
  relationshipKinds: RelationshipKindRef[]
  loading: boolean
  error: string | null
}

/**
 * Fetches all entity lists needed by the workflow builder. Use once at the top of
 * create/edit workflow UI and pass the result to NodeConfigPanel (or provide via context).
 */
export function useWorkflowEngineContext(): WorkflowEngineContextValue {
  const { types: eventTypes, loading: eventTypesLoading, error: eventTypesError } = useEventTypes()

  const [subjectTypes, setSubjectTypes] = useState<SubjectTypeRef[]>([])
  const [subjectTypesLoading, setSubjectTypesLoading] = useState(true)

  const [eventSchemas, setEventSchemas] = useState<EventSchemaRef[]>([])
  const [eventSchemasLoading, setEventSchemasLoading] = useState(true)

  const [transitionRules, setTransitionRules] = useState<EventTransitionRuleRef[]>([])
  const [transitionRulesLoading, setTransitionRulesLoading] = useState(true)

  const [relationshipKinds, setRelationshipKinds] = useState<RelationshipKindRef[]>([])
  const [relationshipKindsLoading, setRelationshipKindsLoading] = useState(true)

  const [otherError, setOtherError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    setSubjectTypesLoading(true)
    timelineApi.subjectTypes
      .list({ limit: 500 })
      .then(({ data, error }) => {
        if (!mounted) return
        if (error) setOtherError(getApiErrorMessage(error, 'Failed to load subject types'))
        else setSubjectTypes(Array.isArray(data) ? data : [])
      })
      .finally(() => {
        if (mounted) setSubjectTypesLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    let mounted = true
    setEventSchemasLoading(true)
    type RawEventSchema = { event_type?: string; version?: number; id?: string }
    timelineApi.eventSchemas
      .list({ limit: 500 })
      .then(({ data }) => {
        if (!mounted) return
        const raw = Array.isArray(data)
          ? data
          : data && typeof data === 'object' && 'items' in data
            ? (data as { items: unknown[] }).items
            : []
        const list: RawEventSchema[] = Array.isArray(raw) ? (raw as RawEventSchema[]) : []
        setEventSchemas(
          list.map((s) => ({
            event_type: s.event_type ?? '',
            version: s.version,
            schema_id: s.id,
          })),
        )
      })
      .finally(() => {
        if (mounted) setEventSchemasLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    let mounted = true
    setTransitionRulesLoading(true)
    timelineApi.eventTransitionRules
      .list({ limit: 500 })
      .then(({ data, error }) => {
        if (!mounted) return
        if (error) setOtherError(getApiErrorMessage(error, 'Failed to load transition rules'))
        else {
          const list = Array.isArray(data) ? data : []
          setTransitionRules(
            list.map((r: { event_type?: string; required_prior_event_types?: string[] }) => ({
              event_type: r.event_type ?? '',
              required_prior_event_types: Array.isArray(r.required_prior_event_types)
                ? r.required_prior_event_types
                : [],
            })),
          )
        }
      })
      .finally(() => {
        if (mounted) setTransitionRulesLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    let mounted = true
    setRelationshipKindsLoading(true)
    timelineApi.relationshipKinds
      .list()
      .then(({ data, error }) => {
        if (!mounted) return
        if (error) setOtherError(getApiErrorMessage(error, 'Failed to load relationship kinds'))
        else {
          const list = Array.isArray(data) ? data : []
          setRelationshipKinds(
            list.map((r: { id?: string; kind?: string; display_name?: string | null }) => ({
              id: r.id ?? '',
              kind: r.kind ?? '',
              display_name: r.display_name ?? null,
            })),
          )
        }
      })
      .finally(() => {
        if (mounted) setRelationshipKindsLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  const loading =
    eventTypesLoading ||
    subjectTypesLoading ||
    eventSchemasLoading ||
    transitionRulesLoading ||
    relationshipKindsLoading
  const error = eventTypesError ?? otherError

  return useMemo(
    () => ({
      eventTypes,
      subjectTypes,
      eventSchemas,
      transitionRules,
      relationshipKinds,
      loading,
      error,
    }),
    [eventTypes, subjectTypes, eventSchemas, transitionRules, relationshipKinds, loading, error],
  )
}
