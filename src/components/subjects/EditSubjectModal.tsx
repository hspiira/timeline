import { useEffect, useState } from 'react'
import type { JsonSchema } from '@/components/shared/JsonSchemaForm'
import { JsonSchemaForm, validateJsonSchema } from '@/components/shared/JsonSchemaForm'
import { FormError, FormField, FormInput } from '@/components/ui/FormField'
import { FormModalActions } from '@/components/ui/FormModalActions'
import { Modal } from '@/components/ui/Modal'
import { useFormSubmit } from '@/hooks/useFormSubmit'
import { useToast } from '@/hooks/useToast'
import { timelineApi } from '@/lib/api-client'
import type { components } from '@/lib/timeline-api'

type SubjectTypeListItem = components['schemas']['SubjectTypeListItem']
type SubjectTypeResponse = components['schemas']['SubjectTypeResponse']

export interface EditSubjectSubject {
  id: string
  subject_type: string
  external_ref?: string | null
  display_name?: string | null
  attributes?: Record<string, unknown> | null
}

interface EditSubjectModalProps {
  isOpen: boolean
  onClose: () => void
  subject: EditSubjectSubject
  subjectTypes?: SubjectTypeListItem[]
  onUpdate: (
    subjectId: string,
    externalRef?: string,
    displayName?: string,
    attributes?: Record<string, unknown>,
  ) => Promise<boolean>
}

function normalizeSchema(schema: unknown): JsonSchema | null {
  if (schema == null) return null
  if (typeof schema === 'string') {
    try {
      const parsed = JSON.parse(schema) as Record<string, unknown>
      return (parsed?.properties ? (parsed as JsonSchema) : null) ?? null
    } catch {
      return null
    }
  }
  if (typeof schema === 'object' && !Array.isArray(schema)) {
    const o = schema as Record<string, unknown>
    return o?.properties ? (schema as JsonSchema) : null
  }
  return null
}

export function EditSubjectModal({
  isOpen,
  onClose,
  subject,
  subjectTypes = [],
  onUpdate,
}: EditSubjectModalProps) {
  const [externalRef, setExternalRef] = useState(subject.external_ref ?? '')
  const [displayName, setDisplayName] = useState(subject.display_name ?? '')
  const [attributes, setAttributes] = useState<Record<string, unknown>>(
    subject.attributes && typeof subject.attributes === 'object' ? { ...subject.attributes } : {},
  )
  const [attributeErrors, setAttributeErrors] = useState<Record<string, string>>({})
  const [attributeSchema, setAttributeSchema] = useState<JsonSchema | null>(null)
  const [schemaLoading, setSchemaLoading] = useState(false)
  const { execute, loading, error, setError } = useFormSubmit()
  const toast = useToast()

  // Sync form when subject changes (e.g. modal opened for another subject)
  useEffect(() => {
    setExternalRef(subject.external_ref ?? '')
    setDisplayName(subject.display_name ?? '')
    setAttributes(
      subject.attributes && typeof subject.attributes === 'object' ? { ...subject.attributes } : {},
    )
    setAttributeErrors({})
  }, [subject.id, subject.external_ref, subject.display_name, subject.attributes])

  // Fetch subject type schema when modal is open and we have subject type
  useEffect(() => {
    if (!isOpen || !subject.subject_type) {
      setAttributeSchema(null)
      return
    }
    const listItem = subjectTypes.find((t) => t.type_name === subject.subject_type)
    if (!listItem?.id) {
      setAttributeSchema(null)
      return
    }
    let mounted = true
    setSchemaLoading(true)
    timelineApi.subjectTypes
      .get(listItem.id)
      .then((res) => {
        if (!mounted) return
        if (res.error || !res.data) {
          setAttributeSchema(null)
          return
        }
        const full = res.data as SubjectTypeResponse
        setAttributeSchema(normalizeSchema(full.schema))
      })
      .catch(() => {
        if (mounted) setAttributeSchema(null)
      })
      .finally(() => {
        if (mounted) setSchemaLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [isOpen, subject.subject_type, subjectTypes])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setAttributeErrors({})

    if (attributeSchema && Object.keys(attributeSchema.properties ?? {}).length > 0) {
      const errors = validateJsonSchema(attributeSchema, attributes)
      if (Object.keys(errors).length > 0) {
        setAttributeErrors(errors)
        setError('Please fix the highlighted attribute fields.')
        toast.error('Validation failed', 'Please fix the highlighted attribute fields.')
        return
      }
    }

    const success = await execute(() =>
      onUpdate(
        subject.id,
        externalRef || undefined,
        displayName || undefined,
        Object.keys(attributes).length ? attributes : undefined,
      ),
    )

    if (success) {
      onClose()
      toast.success('Subject updated', 'Your changes have been saved')
    } else {
      const errorMsg = 'Failed to update subject. Please try again.'
      setError(errorMsg)
      toast.error('Update failed', errorMsg)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Edit Subject" maxWidth="max-w-4xl">
      <form onSubmit={handleSubmit}>
        <div className="space-y-4">
          {error && <FormError message={error} />}

          {/* Subject Type (Read-only) */}
          <FormField label="Subject Type">
            <div className="px-3 py-2 bg-muted rounded-none text-foreground text-sm">
              {subject.subject_type}
            </div>
          </FormField>

          {/* Display name + External Reference in two equal columns */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField label="Display name" hint="Optional human-readable label for this subject">
              <FormInput
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="e.g. John Doe, Order #1234"
                disabled={loading}
              />
            </FormField>
            <FormField
              label="External Reference"
              hint="Leave blank to remove the external reference"
            >
              <FormInput
                type="text"
                value={externalRef}
                onChange={(e) => setExternalRef(e.target.value)}
                placeholder="e.g., external ID or reference"
                disabled={loading}
              />
            </FormField>
          </div>

          {/* Attributes (schema-driven when type has schema) */}
          {schemaLoading && <p className="text-sm text-muted-foreground">Loading type schema...</p>}
          {!schemaLoading && attributeSchema && (
            <FormField label="Attributes" hint="Custom fields for this subject type">
              <JsonSchemaForm
                schema={attributeSchema}
                value={attributes}
                onChange={(v) => {
                  setAttributes(v)
                  if (Object.keys(attributeErrors).length) setAttributeErrors({})
                }}
                errors={attributeErrors}
              />
            </FormField>
          )}
        </div>

        <FormModalActions
          submitLabel="Update Subject"
          loadingLabel="Updating..."
          onCancel={onClose}
          loading={loading}
        />
      </form>
    </Modal>
  )
}
