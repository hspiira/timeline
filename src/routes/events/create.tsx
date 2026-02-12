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
      return
    }

    let mounted = true
    const fetchSchema = async () => {
      setSchemaLoading(true)
      try {
        const res = await timelineApi.eventSchemas.getActive(state.eventType)
        if (!mounted) return

        if (res.data) {
          setSchema(res.data.schema_definition || null)
          setSchemaVersion(res.data.version)
        } else {
          setSchema(null)
          setSchemaVersion(null)
        }
      } catch (err) {
        console.error('Failed to fetch schema:', err)
        setSchema(null)
        setSchemaVersion(null)
      } finally {
        setSchemaLoading(false)
      }
    }

    fetchSchema()
    return () => {
      mounted = false
    }
  }, [state.eventType])

  // Detect document field in schema
  const documentFieldName = useMemo(() => {
    if (!schema?.properties) return null

    const allFields = Object.keys(schema.properties)

    // First, check for explicitly named document fields (required or optional)
    for (const field of allFields) {
      const fieldName = field.toLowerCase()
      if (['documents', 'document_ids', 'attachments', 'evidence', 'supporting_documents'].includes(fieldName)) {
        return field
      }
    }

    // Then look for array fields (required or optional) that could be documents
    for (const field of allFields) {
      const fieldSchema = schema.properties[field]
      // Check if it's an array of strings (likely IDs)
      if (fieldSchema?.type === 'array' && fieldSchema?.items?.type === 'string') {
        const fieldNameLower = field.toLowerCase()
        // Check if name or description suggests documents
        if (
          fieldNameLower.includes('doc') ||
          fieldNameLower.includes('attach') ||
          fieldNameLower.includes('evidence') ||
          fieldNameLower.includes('file') ||
          fieldSchema.description?.toLowerCase().includes('document') ||
          fieldSchema.description?.toLowerCase().includes('attachment')
        ) {
          return field
        }
      }
    }

    return null
  }, [schema])

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

        <form onSubmit={handleSubmit} className="space-y-3 bg-card/80 p-3 rounded-xs border border-border/50">
          {/* API Error Alert */}
          {apiError && (
            <div className="p-2.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xs flex gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-red-900 dark:text-red-200 text-sm">Error</h3>
                <p className="text-sm text-red-800 dark:text-red-300">{apiError}</p>
              </div>
            </div>
          )}

          {/* Subject Selection */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Subject <span className="text-red-500">*</span>
            </label>
            <SubjectSelector value={state.subjectId} onChange={(value) => setState((prev) => ({ ...prev, subjectId: value }))} />
            {state.fieldErrors.subjectId && <p className="text-sm text-red-500 mt-0.5">{state.fieldErrors.subjectId}</p>}
          </div>

          {/* Event Type Selection */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Event Type <span className="text-red-500">*</span>
            </label>
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <EventTypeSelector value={state.eventType} onChange={(value) => setState((prev) => ({ ...prev, eventType: value }))} />
              </div>
              {schemaVersion && (
                <div className="px-2.5 py-1.5 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-xs text-xs">
                  <span className="text-blue-900 dark:text-blue-200 font-medium">Schema v{schemaVersion}</span>
                </div>
              )}
            </div>
            {state.fieldErrors.eventType && <p className="text-sm text-red-500 mt-0.5">{state.fieldErrors.eventType}</p>}
          </div>

          {/* Event Time */}
          <div>
            <label className="block text-sm font-medium mb-1">Event Time</label>
            <Input 
              type="datetime-local"
              value={state.eventTime}
              onChange={(e) => setState((prev) => ({ ...prev, eventTime: e.target.value }))}
              className="w-full px-2.5 py-1.5 bg-background border border-input rounded-xs text-sm"
            />
            <p className="text-sm text-muted-foreground mt-0.5">Defaults to current time</p>
          </div>

          {/* Document Upload - Optional */}
          {state.subjectId && (
            <div>
              <label className="block text-sm font-medium mb-1.5">
                Supporting Documents
                <span className="text-muted-foreground text-xs ml-2">(optional)</span>
              </label>
              <div className="p-3 bg-background/50 rounded-xs border border-border/50">
                <EventDocumentUpload
                  subjectId={state.subjectId}
                  onFilesChanged={(files) => setState((prev) => ({ ...prev, stagedDocuments: files }))}
                  onError={(error) => setApiError(typeof error === 'string' ? error : String(error))}
                  required={false}
                />
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Documents will be uploaded and linked to this event after creation. You can also add documents later.
              </p>
            </div>
          )}

          {/* Payload / Dynamic Form */}
          <div>
            <label className="block text-sm font-medium mb-1.5">
              Event Data
              {schema?.required?.length ? ' ' : ''}
            </label>

            {schemaLoading ? (
              <div className="flex items-center justify-center py-4">
                <LoadingIcon />
                Loading schema...
              </div>
            ) : schema?.properties ? (
              <div className="space-y-2 p-2.5 bg-background/50 rounded-xs border border-border/50">
                <JsonSchemaForm schema={schema} value={state.payload} onChange={handlePayloadChange} errors={state.fieldErrors} />
              </div>
            ) : (
              <div className="text-sm text-muted-foreground italic p-2.5 bg-background/50 rounded-xs border border-border/50">
                Select an event type to see available fields
              </div>
            )}
          </div>

          {/* Actions */}
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
 
