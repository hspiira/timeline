import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { useEffect, useState, useMemo } from 'react'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { timelineApi } from '@/lib/api-client'
import SubjectSelector from '@/components/subjects/SubjectSelector'
import { EventTypeSelector } from '@/components/events'
import { JsonSchemaForm } from '@/components/shared/JsonSchemaForm'
import { EventDocumentUpload } from '@/components/documents/EventDocumentUpload'
import { ErrorModal } from '@/components/ui/ErrorModal'
import type { components } from '@/lib/timeline-api'
import { Input } from '@/components/ui/input'
import { LoadingIcon } from '@/components/ui/icons'
import { Button } from '@/components/ui/button'
import { getApiErrorDisplay } from '@/lib/api-utils'
import { User, ArrowLeft, Calendar, Tag } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { formatFullDateTime } from '@/lib/format-date'

export const Route = createFileRoute('/events/create')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  component: CreateEventPage,
})

interface CreateEventState {
  subjectId: string
  eventType: string
  eventTime: string
  payload: Record<string, any>
  fieldErrors: Record<string, string>
  stagedDocuments: File[]
}

function CreateEventPage() {
  const authState = useRequireAuth()
  const navigate = useNavigate()

  const [state, setState] = useState<CreateEventState>({
    subjectId: '',
    eventType: '',
    eventTime: '',
    payload: {},
    fieldErrors: {},
    stagedDocuments: [],
  })
  const [schema, setSchema] = useState<Record<string, any> | null>(null)
  const [schemaVersion, setSchemaVersion] = useState<number | null>(null)
  const [schemaLoading, setSchemaLoading] = useState(false)
  const [schemaError, setSchemaError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  // Initialize event time after hydration (must be deterministic for SSR)
  // Format for datetime-local input: YYYY-MM-DDTHH:MM in local time
  useEffect(() => {
    const now = new Date()
    // Create local datetime string for the input
    const year = now.getFullYear()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const day = String(now.getDate()).padStart(2, '0')
    const hours = String(now.getHours()).padStart(2, '0')
    const minutes = String(now.getMinutes()).padStart(2, '0')
    const localDateTime = `${year}-${month}-${day}T${hours}:${minutes}`

    setState((prev) => ({
      ...prev,
      eventTime: localDateTime,
    }))
  }, [])

  // Fetch schema when event type changes
  useEffect(() => {
    if (!state.eventType) {
      setSchema(null)
      setSchemaVersion(null)
      setSchemaError(null)
      return
    }

    let mounted = true
    setSchemaError(null)

    const normalizeSchemaDef = (def: unknown): Record<string, any> | null => {
      if (def == null) return null
      if (typeof def === 'string') {
        try {
          return JSON.parse(def) as Record<string, any>
        } catch {
          return null
        }
      }
      return typeof def === 'object' && !Array.isArray(def) ? (def as Record<string, any>) : null
    }

    const applySchema = (data: { schema_definition?: unknown; version?: number }) => {
      const schemaObj = normalizeSchemaDef(data.schema_definition)
      setSchema(schemaObj)
      setSchemaVersion(data.version ?? null)
      setSchemaError(null)
    }

    const fetchSchema = async () => {
      setSchemaLoading(true)
      try {
        const res = await timelineApi.eventSchemas.getActive(state.eventType)
        if (!mounted) return

        if (!res.error && res.data) {
          applySchema(res.data)
          return
        }

        // Fallback: get active failed — try listing versions for this event type and use first
        const listRes = await timelineApi.eventSchemas.listByEventType(state.eventType)
        if (!mounted) return
        if (listRes.data && Array.isArray(listRes.data) && listRes.data.length > 0) {
          const first = listRes.data[0] as { id?: string; version?: number; schema_definition?: unknown }
          const active = listRes.data.find((s: { is_active?: boolean }) => s.is_active)
          const chosen = active ?? first
          const chosenWithDef = chosen as { id?: string; version?: number; schema_definition?: unknown }
          if (chosenWithDef.id) {
            const fullRes = await timelineApi.eventSchemas.get(chosenWithDef.id)
            if (!mounted) return
            if (!fullRes.error && fullRes.data) {
              applySchema(fullRes.data)
              return
            }
          }
          if (chosenWithDef.schema_definition != null) {
            const schemaObj = normalizeSchemaDef(chosenWithDef.schema_definition)
            setSchema(schemaObj)
            setSchemaVersion(chosenWithDef.version ?? null)
            setSchemaError(null)
            return
          }
        }

        setSchemaError(
          res.error
            ? 'No active schema for this event type. Create one in Settings → Event Schemas and set it active.'
            : 'No schema found for this event type'
        )
        setSchema(null)
        setSchemaVersion(null)
      } catch (err) {
        console.error('Failed to fetch schema:', err)
        setSchemaError(err instanceof Error ? err.message : 'Failed to load schema')
        setSchema(null)
        setSchemaVersion(null)
      } finally {
        if (mounted) setSchemaLoading(false)
      }
    }

    fetchSchema()
    return () => {
      mounted = false
    }
  }, [state.eventType])

  // Validate payload against schema
  const validatePayload = useMemo(() => {
    const errors: Record<string, string> = {}

    if (!schema?.properties) return errors

    const requiredFields = schema?.required ?? []

    for (const field of requiredFields) {
      if (!state.payload[field]) {
        errors[field] = `${field} is required`
      }
    }

    return errors
  }, [schema, state.payload])

  const handlePayloadChange = (newPayload: Record<string, any>) => {
    setState((prev) => ({
      ...prev,
      payload: newPayload,
      fieldErrors: {},
    }))
    setApiError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setApiError(null)

    // Validate required fields
    const errors: Record<string, string> = {}
    if (!state.subjectId) errors.subjectId = 'Subject is required'
    if (!state.eventType) errors.eventType = 'Event type is required'

    if (Object.keys(validatePayload).length > 0) {
      setState((prev) => ({
        ...prev,
        fieldErrors: validatePayload,
      }))
      return
    }


    if (Object.keys(errors).length > 0) {
      setState((prev) => ({
        ...prev,
        fieldErrors: errors,
      }))
      return
    }

    setLoading(true)
    try {
      // Validate schema version is available
      if (!schemaVersion) {
        setApiError('Schema version not available. Please select an event type.')
        setLoading(false)
        return
      }

      // Create event with payload (documents are optional now)
      const eventCreateData: components['schemas']['EventCreateRequest'] = {
        subject_id: state.subjectId,
        event_type: state.eventType,
        schema_version: schemaVersion,
        event_time: new Date(state.eventTime).toISOString(),
        payload: state.payload,
      }

      const { data, error: createError, response } = await timelineApi.events.create(eventCreateData)

      if (createError) {
        const display = getApiErrorDisplay(
          { error: createError, status: response?.status },
          'Failed to create event'
        )
        setApiError(display.message)
        if (display.fieldErrors && display.fieldErrors.length > 0) {
          setState((prev) => ({
            ...prev,
            fieldErrors: {
              ...prev.fieldErrors,
              ...Object.fromEntries(
                display.fieldErrors!.map((e) => {
                  const key = e.field.replace(/^payload\.?/, '') || 'payload'
                  return [key, e.message]
                })
              ),
            },
          }))
        }
        setLoading(false)
        return
      }

      if (!data?.id) {
        setApiError('Failed to create event: no event ID returned')
        setLoading(false)
        return
      }

      // Upload and link documents to the created event (if any)
      if (state.stagedDocuments.length > 0) {
        try {
          await Promise.all(
            state.stagedDocuments.map(async (file) => {
              const formData = new FormData()
              formData.append('file', file)
              formData.append('subject_id', state.subjectId)
              formData.append('event_id', data.id)
              formData.append('document_type', 'evidence')

              const { error } = await timelineApi.documents.upload(formData)
              if (error) {
                console.warn('Failed to link document to event:', error)
                // Don't fail - event was created successfully
              }
            })
          )
        } catch (err) {
          console.warn('Error uploading documents:', err)
          // Event was created successfully, documents optional
        }
      }

      // Navigate to events list
      navigate({ to: '/events' })
    } catch (err) {
      console.error('Error creating event:', err)
      setApiError('An unexpected error occurred while creating the event')
    } finally {
      setLoading(false)
    }
  }

  // Same output on server and first client paint to avoid hydration mismatch (auth/store can differ)
  if (!mounted || authState.isLoading) {
    return (
      <div className="min-h-[calc(100vh-4rem)] bg-background flex items-center justify-center">
        <div className="flex items-center gap-2 text-muted-foreground">
          <LoadingIcon />
          <span className="text-sm">Loading...</span>
        </div>
      </div>
    )
  }

  if (!authState.user) return null

  const errorMessage = apiError ?? (schemaError ? `Could not load schema for "${state.eventType}". ${schemaError}` : null)

  return (
    <>
        <ErrorModal
          open={!!errorMessage}
          onClose={() => {
            setApiError(null)
            setSchemaError(null)
          }}
          title="Error"
          message={errorMessage ?? ''}
        />

        <div className="flex items-center gap-3 mb-4">
          <Link
            to="/events"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Events
          </Link>
          <h1 className="text-lg font-bold text-foreground">Create Event</h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Summary when enough context is set */}
          {state.subjectId && state.eventType && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-none border border-border/50 bg-muted/20 text-sm text-muted-foreground">
              <Tag className="w-4 h-4 shrink-0" />
              <span>
                Recording: <span className="font-mono text-foreground">{state.subjectId}</span>
                {' · '}
                <span className="font-medium text-foreground">{state.eventType}</span>
                {schemaVersion != null && <span className="font-mono"> v{schemaVersion}</span>}
                {' · '}
                {formatFullDateTime(new Date(state.eventTime).toISOString())}
              </span>
            </div>
          )}

          {/* Section: When & context */}
          <section className="space-y-4 bg-card/80 p-5 rounded-none border border-border/50">
            <h2 className="text-sm font-semibold text-foreground border-b border-border/50 pb-2 -mt-0.5">
              When & context
            </h2>
            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  Subject <span className="text-destructive">*</span>
                </label>
                <SubjectSelector value={state.subjectId} onChange={(value) => setState((prev) => ({ ...prev, subjectId: value }))} />
                {state.fieldErrors.subjectId && <p className="text-sm text-destructive mt-1">{state.fieldErrors.subjectId}</p>}
              </div>

              <div className="min-h-[3.5rem]">
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  Event Type <span className="text-destructive">*</span>
                </label>
                <div className="flex items-stretch gap-2">
                  <div className="flex-1 min-w-0">
                    <EventTypeSelector value={state.eventType} onChange={(value) => setState((prev) => ({ ...prev, eventType: value }))} />
                  </div>
                  {schemaVersion != null && (
                    <div className="px-2.5 py-1.5 bg-muted rounded-none text-xs flex items-center">
                      <span className="text-muted-foreground font-medium">v{schemaVersion}</span>
                    </div>
                  )}
                </div>
                {state.fieldErrors.eventType && <p className="text-sm text-destructive mt-1">{state.fieldErrors.eventType}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  <span className="inline-flex items-center gap-1.5"><Calendar className="w-3.5 h-3.5" /> Event time</span>
                </label>
                <Input
                  type="datetime-local"
                  value={state.eventTime}
                  onChange={(e) => setState((prev) => ({ ...prev, eventTime: e.target.value }))}
                  className="w-full px-2.5 py-1.5 bg-background border border-input rounded-none text-sm"
                />
                <p className="text-xs text-muted-foreground mt-1">When the event occurred (local time). Defaults to now.</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1.5">
                  <span className="inline-flex items-center gap-1.5"><User className="w-3.5 h-3.5" /> Recording as</span>
                </label>
                <div className="px-2.5 py-1.5 rounded-none border border-border/50 bg-muted/30 text-sm text-foreground">
                  {authState.user?.username ?? '—'}
                  {authState.user?.email && (
                    <span className="text-muted-foreground ml-1.5">({authState.user.email})</span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-1">Set by the system; you are recorded as the creator of this event.</p>
              </div>
            </div>
          </section>

          {/* Section: Event data */}
          <section className="space-y-4 bg-card/80 p-5 rounded-none border border-border/50">
            <h2 className="text-sm font-semibold text-foreground border-b border-border/50 pb-2 -mt-0.5">
              Event data
              {schema?.required?.length ? <span className="text-destructive ml-0.5">*</span> : ''}
            </h2>
            {schemaLoading ? (
              <div className="flex items-center justify-center py-8 rounded-none border border-border/50 bg-muted/30">
                <LoadingIcon />
                <span className="ml-2 text-sm text-muted-foreground">Loading schema...</span>
              </div>
            ) : schemaError ? (
              <div className="text-sm text-muted-foreground italic p-4 rounded-none border border-border/50 bg-muted/20">
                Could not load schema for this event type.
              </div>
            ) : schema?.properties ? (
              <div className="space-y-3 p-4 rounded-none border border-border/50 bg-muted/20">
                <JsonSchemaForm schema={schema} value={state.payload} onChange={handlePayloadChange} errors={state.fieldErrors} />
              </div>
            ) : (
              <div className="text-sm text-muted-foreground italic p-4 rounded-none border border-border/50 bg-muted/20">
                {state.eventType ? 'No fields defined for this event type.' : 'Select an event type to see available fields'}
              </div>
            )}
          </section>

          {state.subjectId && (
            <section className="space-y-4 bg-card/80 p-5 rounded-none border border-border/50">
              <h2 className="text-sm font-semibold text-foreground border-b border-border/50 pb-2 -mt-0.5">
                Supporting documents <span className="text-muted-foreground font-normal">(optional)</span>
              </h2>
              <div className="p-4 rounded-none border border-dashed border-border bg-muted/10">
                <EventDocumentUpload
                  subjectId={state.subjectId}
                  onFilesChanged={(files) => setState((prev) => ({ ...prev, stagedDocuments: files }))}
                  onError={(error) => setApiError(typeof error === 'string' ? error : String(error))}
                  required={false}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Files are uploaded and linked to this event after creation. You can add more later.
              </p>
            </section>
          )}

          <div className="flex items-center gap-2 pt-2">
            <Button
              type="submit"
              disabled={loading || schemaLoading}
              variant="primary"
              size="sm"
            >
              {loading ? (
                <>
                  <LoadingIcon />
                  Creating...
                </>
              ) : (
                'Create Event'
              )}
            </Button>
            <Button
              type="button"
              onClick={() => navigate({ to: '/events' })}
              variant="ghost"
              size="sm"
            >
              Cancel
            </Button>
          </div>
        </form>
    </>
  )
}
 
