import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect, useState, useMemo } from 'react'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { timelineApi } from '@/lib/api-client'
import SubjectSelector from '@/components/subjects/SubjectSelector'
import EventTypeSelector from '@/components/events/EventTypeSelector'
import { JsonSchemaForm } from '@/components/shared/JsonSchemaForm'
import { EventDocumentUpload } from '@/components/documents/EventDocumentUpload'
import { AlertCircle } from 'lucide-react'
import type { components } from '@/lib/timeline-api'
import { Input } from '@/components/ui/input'
import { LoadingIcon } from '@/components/ui/icons'
import { Button } from '@/components/ui/button'

export const Route = createFileRoute('/events/create')({
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
          if (chosen.id) {
            const fullRes = await timelineApi.eventSchemas.get(chosen.id)
            if (!mounted) return
            if (!fullRes.error && fullRes.data) {
              applySchema(fullRes.data)
              return
            }
          }
          if (chosen.schema_definition != null) {
            const schemaObj = normalizeSchemaDef(chosen.schema_definition)
            setSchema(schemaObj)
            setSchemaVersion(chosen.version ?? null)
            setSchemaError(null)
            return
          }
        }

        if (res.error) {
          const msg =
            typeof res.error === 'object' && res.error !== null && 'message' in res.error
              ? String((res.error as { message?: string }).message)
              : typeof res.error === 'object' && res.error !== null && 'detail' in res.error
                ? String((res.error as { detail?: string }).detail)
                : 'Schema not found or not active'
          setSchemaError(msg)
        } else {
          setSchemaError('No schema found for this event type')
        }
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

      const { data, error: createError } = await timelineApi.events.create(eventCreateData)

      if (createError) {
        const errorMessage =
          typeof createError === 'object' && 'message' in createError
            ? (createError as any).message
            : 'Failed to create event'
        setApiError(errorMessage)
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

  if (authState.isLoading) {
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

  return (
    <>
        <h1 className="text-lg font-bold mb-3">Create Event</h1>

        <form onSubmit={handleSubmit} className="space-y-5 bg-card/80 p-5 rounded-none border border-border/50">
          {apiError && (
            <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-none flex gap-2" role="alert">
              <AlertCircle className="w-4 h-4 text-destructive shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-foreground text-sm">Error</h3>
                <p className="text-sm text-muted-foreground">{apiError}</p>
              </div>
            </div>
          )}

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

            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-foreground mb-1.5">Event Time</label>
              <Input
                type="datetime-local"
                value={state.eventTime}
                onChange={(e) => setState((prev) => ({ ...prev, eventTime: e.target.value }))}
                className="w-full max-w-sm px-2.5 py-1.5 bg-background border border-input rounded-none text-sm"
              />
              <p className="text-xs text-muted-foreground mt-1">Defaults to current time</p>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-1.5">
              Event Data
              {schema?.required?.length ? <span className="text-destructive ml-0.5">*</span> : ''}
            </label>
            {schemaLoading ? (
              <div className="flex items-center justify-center py-8 rounded-none border border-border/50 bg-muted/30">
                <LoadingIcon />
                <span className="ml-2 text-sm text-muted-foreground">Loading schema...</span>
              </div>
            ) : schemaError ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-none text-sm text-destructive">
                Could not load schema for &quot;{state.eventType}&quot;. {schemaError}
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
          </div>

          {state.subjectId && (
            <div className="pt-4 border-t border-border/50">
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Supporting Documents <span className="text-muted-foreground font-normal">(optional)</span>
              </label>
              <div className="p-4 rounded-none border border-dashed border-border bg-muted/10">
                <EventDocumentUpload
                  subjectId={state.subjectId}
                  onFilesChanged={(files) => setState((prev) => ({ ...prev, stagedDocuments: files }))}
                  onError={(error) => setApiError(typeof error === 'string' ? error : String(error))}
                  required={false}
                />
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Files are uploaded and linked to this event after creation. You can add more later.
              </p>
            </div>
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
 
