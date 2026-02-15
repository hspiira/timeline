import { useState, useEffect } from 'react'
import { useToast } from '@/hooks/useToast'
import { useFormSubmit } from '@/hooks/useFormSubmit'
import { FormField, FormInput, FormError } from '@/components/ui/FormField'
import { FormModalActions } from '@/components/ui/FormModalActions'
import { Modal } from '@/components/ui/Modal'
import { Select } from '@/components/ui/select'
import { JsonSchemaForm } from '@/components/shared/JsonSchemaForm'
import type { JsonSchema } from '@/components/shared/JsonSchemaForm'
import { validateAlphanumericUnderscore } from '@/lib/validation'
import { timelineApi } from '@/lib/api-client'
import type { components } from '@/lib/timeline-api'

type SubjectTypeListItem = components['schemas']['SubjectTypeListItem']
type SubjectTypeResponse = components['schemas']['SubjectTypeResponse']

/** Same shape as filter options: used to drive the subject type dropdown (linked to subject types list). */
export type SubjectTypeOption = { type_name: string; display_name: string }

interface CreateSubjectModalProps {
  isOpen: boolean
  onClose: () => void
  onCreate: (
    subjectType: string,
    externalRef?: string,
    displayName?: string,
    attributes?: Record<string, unknown>
  ) => Promise<boolean>
  /** Subject types from API (GET /subject-types). Used for schema fetch by id. */
  subjectTypes?: SubjectTypeListItem[]
  /** Options for the type dropdown. Should be from Subject types only (Settings → Subject types), not event schemas. */
  subjectTypeOptions?: SubjectTypeOption[]
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

export function CreateSubjectModal({
  isOpen,
  onClose,
  onCreate,
  subjectTypes = [],
  subjectTypeOptions,
}: CreateSubjectModalProps) {
  const [subjectType, setSubjectType] = useState('')
  const [externalRef, setExternalRef] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [attributes, setAttributes] = useState<Record<string, unknown>>({})
  const [attributeSchema, setAttributeSchema] = useState<JsonSchema | null>(null)
  const [schemaLoading, setSchemaLoading] = useState(false)
  const { execute, loading, error, setError } = useFormSubmit()
  const toast = useToast()

  // Use dropdown when we have options (merged list from parent = linked to subject types list)
  const options = subjectTypeOptions?.length
    ? subjectTypeOptions
    : subjectTypes.map((t) => ({ type_name: t.type_name, display_name: t.display_name || t.type_name }))
  const useDropdown = options.length > 0

  // When subject type is selected (and we have list), fetch full type to get schema (need id from subjectTypes)
  useEffect(() => {
    if (!subjectType || !useDropdown) {
      setAttributeSchema(null)
      setAttributes({})
      return
    }
    const listItem = subjectTypes.find((t) => t.type_name === subjectType)
    if (!listItem?.id) {
      setAttributeSchema(null)
      setAttributes({})
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
          setAttributes({})
          return
        }
        const full = res.data as SubjectTypeResponse
        const schema = normalizeSchema(full.schema)
        setAttributeSchema(schema)
        setAttributes((prev) => (schema ? prev : {}))
      })
      .catch(() => {
        if (mounted) {
          setAttributeSchema(null)
          setAttributes({})
        }
      })
      .finally(() => {
        if (mounted) setSchemaLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [subjectType, useDropdown, subjectTypes])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const value = useDropdown ? subjectType : subjectType.trim().toLowerCase()
    if (!value) {
      setError('Subject type is required')
      return
    }
    if (!useDropdown) {
      const validationError = validateAlphanumericUnderscore(value, 'Subject type')
      if (validationError) {
        setError(validationError)
        toast.error('Validation error', validationError)
        return
      }
    }

    const success = await execute(() =>
      onCreate(
        value,
        externalRef || undefined,
        displayName || undefined,
        Object.keys(attributes).length ? attributes : undefined
      )
    )

    if (success) {
      setSubjectType('')
      setExternalRef('')
      setDisplayName('')
      setAttributes({})
      onClose()
    } else {
      const createError = 'Failed to create subject. Please try again.'
      setError(createError)
    }
  }

  if (!isOpen) return null

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Create Subject"
      maxWidth="max-w-2xl"
    >
      <form onSubmit={handleSubmit}>
        <div className="space-y-4">
          {error && <FormError message={error} />}

          {/* Subject Type - full width */}
          <FormField
            label="Subject Type"
            required
            hint={
              useDropdown
                ? 'Choose from configured types (Settings → Subject types)'
                : 'Alphanumeric characters and underscores only'
            }
          >
            {useDropdown ? (
              <Select
                value={subjectType}
                onChange={(e) => setSubjectType(e.target.value)}
                disabled={loading}
              >
                <option value="">Select type...</option>
                {options.map((opt) => (
                  <option key={opt.type_name} value={opt.type_name}>
                    {opt.display_name}
                  </option>
                ))}
              </Select>
            ) : (
              <FormInput
                type="text"
                value={subjectType}
                onChange={(e) => setSubjectType(e.target.value)}
                placeholder="e.g., user, order, project"
                disabled={loading}
                autoFocus
              />
            )}
          </FormField>

          {/* Display name + External ref on one row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField
              label="Display name"
              hint="Optional human-readable label"
            >
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
              hint="Optional - leave blank if not needed"
            >
              <FormInput
                type="text"
                value={externalRef}
                onChange={(e) => setExternalRef(e.target.value)}
                placeholder="e.g., external ID"
                disabled={loading}
              />
            </FormField>
          </div>

          {/* Attributes (schema-driven when type has schema) */}
          {schemaLoading && (
            <p className="text-sm text-muted-foreground">Loading type schema...</p>
          )}
          {!schemaLoading && attributeSchema && (
            <FormField label="Attributes" hint="Custom fields for this subject type">
              <JsonSchemaForm
                schema={attributeSchema}
                value={attributes}
                onChange={setAttributes}
              />
            </FormField>
          )}
        </div>

        <FormModalActions
          submitLabel="Create Subject"
          loadingLabel="Creating..."
          onCancel={onClose}
          loading={loading}
        />
      </form>
    </Modal>
  )
}
