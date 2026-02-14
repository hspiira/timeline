import { useState } from 'react'
import { Plus, Trash2, Eye, EyeOff } from 'lucide-react'
import { useFormSubmit } from '@/hooks/useFormSubmit'
import { Modal } from '@/components/ui/Modal'
import { FormError, FormField, FormInput, FormTextarea } from '@/components/ui/FormField'
import { FormModalActions } from '@/components/ui/FormModalActions'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { validateAlphanumericUnderscore } from '@/lib/validation'

interface SchemaField {
  id: string
  name: string
  type: string
  required: boolean
  description: string
  enum?: string[]
  minimum?: number
  maximum?: number
  pattern?: string
  format?: string
}

interface EditingField extends SchemaField {}

interface SchemaFormModalProps {
  onClose: () => void
  onSubmit: (eventType: string, definition: Record<string, any>) => Promise<boolean>
  title: string
}

const FIELD_TYPES = [
  { value: 'string', label: 'Text' },
  { value: 'enum', label: 'Dropdown/Enum' },
  { value: 'email', label: 'Email' },
  { value: 'number', label: 'Number' },
  { value: 'integer', label: 'Integer' },
  { value: 'boolean', label: 'True/False' },
  { value: 'date', label: 'Date' },
  { value: 'datetime', label: 'Date & Time' },
  { value: 'phone', label: 'Phone' },
  { value: 'url', label: 'URL' },
]

const STRING_FORMATS = [
  { value: 'email', label: 'Email' },
  { value: 'uri', label: 'URL' },
  { value: 'date', label: 'Date' },
  { value: 'date-time', label: 'Date & Time' },
  { value: 'phone', label: 'Phone' },
]

export function SchemaFormModal({ onClose, onSubmit, title }: SchemaFormModalProps) {
  const [eventType, setEventType] = useState('')
  const [fields, setFields] = useState<SchemaField[]>([])
  const { execute, loading, error, setError } = useFormSubmit()
  const [showJsonPreview, setShowJsonPreview] = useState(false)
  const [editingField, setEditingField] = useState<EditingField | null>(null)
  const [editMode, setEditMode] = useState<'form' | 'json'>('form')
  const [jsonEdit, setJsonEdit] = useState('')

  const validateEventType = (value: string): string | null =>
    validateAlphanumericUnderscore(value, 'Event type')

  const generateJsonSchema = (): Record<string, any> => {
    const properties: Record<string, any> = {}
    const required: string[] = []

    fields.forEach((field) => {
      const fieldSchema: Record<string, any> = {}

      // Set type and format based on field type
      if (field.type === 'enum') {
        fieldSchema.type = 'string'
        if (field.enum && field.enum.length > 0) {
          fieldSchema.enum = field.enum
        }
      } else if (field.type === 'email') {
        fieldSchema.type = 'string'
        fieldSchema.format = 'email'
      } else if (field.type === 'phone') {
        fieldSchema.type = 'string'
        fieldSchema.pattern = '^\\+?[1-9]\\d{1,14}$'
      } else if (field.type === 'url') {
        fieldSchema.type = 'string'
        fieldSchema.format = 'uri'
      } else if (field.type === 'date') {
        fieldSchema.type = 'string'
        fieldSchema.format = 'date'
      } else if (field.type === 'datetime') {
        fieldSchema.type = 'string'
        fieldSchema.format = 'date-time'
      } else if (field.type === 'string') {
        fieldSchema.type = 'string'
        // Apply custom format if specified
        if (field.format) {
          fieldSchema.format = field.format
        }
        // Apply custom pattern if specified
        if (field.pattern) {
          fieldSchema.pattern = field.pattern
        }
      } else {
        fieldSchema.type = field.type
      }

      // Add numeric constraints
      if ((field.type === 'number' || field.type === 'integer') && field.minimum !== undefined) {
        fieldSchema.minimum = field.minimum
      }
      if ((field.type === 'number' || field.type === 'integer') && field.maximum !== undefined) {
        fieldSchema.maximum = field.maximum
      }

      // Add description if provided
      if (field.description) {
        fieldSchema.description = field.description
      }

      properties[field.name] = fieldSchema

      // Track required fields
      if (field.required) {
        required.push(field.name)
      }
    })

    return {
      type: 'object',
      properties,
      ...(required.length > 0 && { required }),
    }
  }

  const parseJsonSchema = (jsonStr: string): boolean => {
    try {
      const schema = JSON.parse(jsonStr)

      if (!schema.properties || typeof schema.properties !== 'object') {
        setError('JSON must have a "properties" object')
        return false
      }

      const parsedFields: SchemaField[] = []
      const requiredFields = schema.required || []

      Object.entries(schema.properties).forEach(([name, propSchema]: [string, any]) => {
        const field: SchemaField = {
          id: crypto.randomUUID(),
          name,
          type: 'string',
          required: requiredFields.includes(name),
          description: propSchema.description || '',
        }

        // Determine type from schema
        if (propSchema.enum) {
          field.type = 'enum'
          field.enum = propSchema.enum
        } else if (propSchema.format === 'email') {
          field.type = 'email'
        } else if (propSchema.format === 'date') {
          field.type = 'date'
        } else if (propSchema.format === 'date-time') {
          field.type = 'datetime'
        } else if (propSchema.format === 'uri') {
          field.type = 'url'
        } else if (propSchema.type === 'string') {
          if (propSchema.pattern === '^\\+?[1-9]\\d{1,14}$') {
            field.type = 'phone'
          } else {
            field.type = 'string'
            if (propSchema.format) field.format = propSchema.format
            if (propSchema.pattern) field.pattern = propSchema.pattern
          }
        } else if (propSchema.type === 'number') {
          field.type = 'number'
          if (propSchema.minimum !== undefined) field.minimum = propSchema.minimum
          if (propSchema.maximum !== undefined) field.maximum = propSchema.maximum
        } else if (propSchema.type === 'integer') {
          field.type = 'integer'
          if (propSchema.minimum !== undefined) field.minimum = propSchema.minimum
          if (propSchema.maximum !== undefined) field.maximum = propSchema.maximum
        } else if (propSchema.type) {
          field.type = propSchema.type
        }

        parsedFields.push(field)
      })

      setFields(parsedFields)
      setError(null)
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid JSON')
      return false
    }
  }

  const switchToJsonMode = () => {
    setJsonEdit(JSON.stringify(generateJsonSchema(), null, 2))
    setEditMode('json')
  }

  const switchToFormMode = () => {
    if (parseJsonSchema(jsonEdit)) {
      setEditMode('form')
    }
  }

  const startAddingField = () => {
    const newField: EditingField = {
      id: Date.now().toString(),
      name: '',
      type: 'string',
      required: false,
      description: '',
    }
    setEditingField(newField)
  }

  const startEditingField = (id: string) => {
    const field = fields.find((f) => f.id === id)
    if (field) {
      setEditingField({ ...field })
    }
  }

  const saveField = () => {
    if (!editingField) return

    const existingIndex = fields.findIndex((f) => f.id === editingField.id)
    if (existingIndex >= 0) {
      // Updating existing field
      const updated = [...fields]
      updated[existingIndex] = editingField
      setFields(updated)
    } else {
      // Adding new field
      setFields([...fields, editingField])
    }
    setEditingField(null)
  }

  const removeField = (id: string) => {
    setFields(fields.filter((f) => f.id !== id))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validate event type
    const eventTypeError = validateEventType(eventType)
    if (eventTypeError) {
      setError(eventTypeError)
      return
    }

    let schema: Record<string, any>

    if (editMode === 'json') {
      // Parse and validate JSON
      try {
        schema = JSON.parse(jsonEdit)
        if (!schema.properties || typeof schema.properties !== 'object') {
          setError('JSON must have a "properties" object')
          return
        }
        if (Object.keys(schema.properties).length === 0) {
          setError('Schema must have at least one property')
          return
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Invalid JSON')
        return
      }
    } else {
      // Validate fields
      if (fields.length === 0) {
        setError('Add at least one field to create a schema')
        return
      }

      // Validate field names
      for (const field of fields) {
        const err = validateAlphanumericUnderscore(field.name, 'Field name')
        if (err) {
          setError(field.name.trim() ? err.replace('Field name', `Field name "${field.name}"`) : 'All field names are required')
          return
        }
      }

      // Check for duplicate field names
      const fieldNames = fields.map((f) => f.name)
      if (new Set(fieldNames).size !== fieldNames.length) {
        setError('Field names must be unique')
        return
      }

      schema = generateJsonSchema()
    }

    const success = await execute(() => onSubmit(eventType.toLowerCase(), schema))
    if (success) {
      onClose()
    } else {
      setError('Failed to create schema. Please try again.')
    }
  }

  const jsonSchema = generateJsonSchema()

  return (
    <>
      <Modal isOpen={true} onClose={onClose} title={title} maxWidth="max-w-3xl" closeButton={!loading}>
      <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-6">
          {/* Error Alert */}
          {error && <FormError message={error} />}

          {/* Mode Toggle */}
          <div className="flex items-center gap-2">
            <Button
              type="button"
              onClick={() => editMode === 'json' ? switchToFormMode() : null}
              variant={editMode === 'form' ? 'primary' : 'ghost'}
              size="sm"
              disabled={editMode === 'form'}
            >
              Form
            </Button>
            <Button
              type="button"
              onClick={() => editMode === 'form' ? switchToJsonMode() : null}
              variant={editMode === 'json' ? 'primary' : 'ghost'}
              size="sm"
              disabled={editMode === 'json'}
            >
              JSON
            </Button>
          </div>

          {editMode === 'form' ? (
            <>
              <FormField
                label="Event Type"
                required
                hint="Alphanumeric characters and underscores only (will be lowercase)"
              >
                <FormInput
                  type="text"
                  value={eventType}
                  onChange={(e) => setEventType(e.target.value)}
                  placeholder="e.g., user_created, order_placed, payment_received"
                  disabled={loading}
                />
              </FormField>

              {/* Fields Summary */}
              <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-foreground/90">Event Fields</h3>
              <Button
                type="button"
                onClick={startAddingField}
                disabled={loading}
                size="sm"
                variant="primary"
              >
                <Plus className="w-3 h-3" />
                Add Field
              </Button>
            </div>

            {fields.length === 0 ? (
              <div className="p-4 bg-background/50 border border-dashed border-border rounded-none text-center text-sm text-muted-foreground">
                No fields yet. Click "Add Field" to create one.
              </div>
            ) : (
              <div className="space-y-2">
                {fields.map((field, index) => {
                  const typeLabel = FIELD_TYPES.find((t) => t.value === field.type)?.label || field.type
                  return (
                    <div
                      key={field.id}
                      className="flex items-center justify-between p-3 bg-background/50 border border-border rounded-none hover:border-primary/50 transition-colors group"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-semibold text-muted-foreground">#{index + 1}</span>
                          <span className="font-medium text-foreground">{field.name}</span>
                          <span className="px-2 py-0.5 text-xs bg-primary/10 text-primary rounded-none">
                            {typeLabel}
                          </span>
                          {field.required && (
                            <span className="px-1.5 py-0.5 text-xs font-medium bg-orange-100 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 rounded-none">
                              Required
                            </span>
                          )}
                          {field.enum && field.enum.length > 0 && (
                            <span className="px-1.5 py-0.5 text-xs font-medium bg-purple-100 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 rounded-none">
                              {field.enum.length} options
                            </span>
                          )}
                          {(field.minimum !== undefined || field.maximum !== undefined) && (
                            <span className="px-1.5 py-0.5 text-xs font-medium bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-none">
                              {field.minimum !== undefined && field.maximum !== undefined
                                ? `${field.minimum}-${field.maximum}`
                                : field.minimum !== undefined
                                ? `≥ ${field.minimum}`
                                : `≤ ${field.maximum}`}
                            </span>
                          )}
                          {field.format && (
                            <span className="px-1.5 py-0.5 text-xs font-medium bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded-none">
                              {field.format}
                            </span>
                          )}
                          {field.pattern && (
                            <span className="px-1.5 py-0.5 text-xs font-medium bg-yellow-100 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300 rounded-none">
                              Regex pattern
                            </span>
                          )}
                        </div>
                        {field.description && (
                          <p className="text-xs text-muted-foreground mt-1">{field.description}</p>
                        )}
                      </div>

                      <div className="flex items-center gap-2 ml-4 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button
                          type="button"
                          onClick={() => startEditingField(field.id)}
                          size="sm"
                          variant="outline"
                        >
                          Edit
                        </Button>
                        <Button
                          type="button"
                          onClick={() => removeField(field.id)}
                          size="sm"
                          variant="ghost"
                        >
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

              {/* JSON Preview */}
              {fields.length > 0 && (
                <div>
                  <button
                    type="button"
                    onClick={() => setShowJsonPreview(!showJsonPreview)}
                    className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-2"
                  >
                    {showJsonPreview ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                    {showJsonPreview ? 'Hide' : 'Preview'} Generated JSON
                  </button>

                  {showJsonPreview && (
                    <div className="p-3 bg-background/50 border border-border rounded-none overflow-auto max-h-40">
                      <pre className="text-xs font-mono text-muted-foreground whitespace-pre-wrap wrap-break-word">
                        {JSON.stringify(jsonSchema, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <>
              <FormField
                label="Event Type"
                required
                hint="Alphanumeric characters and underscores only (will be lowercase)"
              >
                <FormInput
                  type="text"
                  value={eventType}
                  onChange={(e) => setEventType(e.target.value)}
                  placeholder="e.g., user_created, order_placed, payment_received"
                  disabled={loading}
                />
              </FormField>

              <FormField
                label="JSON Schema"
                required
                hint="Edit the JSON schema directly. Changes will be reflected when you switch back to form mode."
              >
                <FormTextarea
                  value={jsonEdit}
                  onChange={(e) => setJsonEdit(e.target.value)}
                  placeholder='{\n  "type": "object",\n  "properties": {\n    "email": {\n      "type": "string",\n      "format": "email"\n    }\n  },\n  "required": ["email"]\n}'
                  className="font-mono text-xs"
                  rows={12}
                  disabled={loading}
                />
              </FormField>
            </>
          )}

          <FormModalActions
            submitLabel="Create Schema"
            loadingLabel="Creating..."
            onCancel={onClose}
            loading={loading}
            submitDisabled={editMode === 'form' ? fields.length === 0 : !jsonEdit.trim()}
          />
        </form>
      </Modal>

      {/* Field Editor Modal */}
      <Modal
        isOpen={!!editingField}
        onClose={() => setEditingField(null)}
        title={
          editingField && fields.some((f) => f.id === editingField.id) ? 'Edit Field' : 'Add Field'
        }
        maxWidth="max-w-md"
        zIndex={60}
      >
        {editingField && (
          <div className="space-y-4">
            <FormField label="Field Name" required>
              <FormInput
                type="text"
                value={editingField.name}
                onChange={(e) => setEditingField({ ...editingField, name: e.target.value })}
                placeholder="e.g., user_email"
              />
            </FormField>

          <FormField label="Type">
            <Select
              value={editingField.type}
              onChange={(e) => setEditingField({ ...editingField, type: e.target.value })}
            >
              {FIELD_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </Select>
          </FormField>

            <FormField label="Description (optional)">
            <FormInput
              type="text"
              value={editingField.description}
              onChange={(e) => setEditingField({ ...editingField, description: e.target.value })}
              placeholder="What does this field represent?"
            />
          </FormField>

          {/* Required */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={editingField.required}
              onChange={(e) => setEditingField({ ...editingField, required: e.target.checked })}
              className="rounded-none"
            />
            <span className="text-sm font-medium text-foreground/90">Required field</span>
          </label>

          {/* Enum Values - for enum type */}
          {editingField.type === 'enum' && (
            <div>
              <label className="block text-sm font-medium text-foreground/90 mb-2">
                Enum Values <span className="text-destructive">*</span>
              </label>
              <div className="space-y-2 mb-2">
                {(editingField.enum || []).map((value, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <Input
                      type="text"
                      value={value}
                      onChange={(e) => {
                        const newEnum = [...(editingField.enum || [])]
                        newEnum[idx] = e.target.value
                        setEditingField({ ...editingField, enum: newEnum })
                      }}
                      className="flex-1"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        const newEnum = (editingField.enum || []).filter((_, i) => i !== idx)
                        setEditingField({ ...editingField, enum: newEnum })
                      }}
                      className="p-1 hover:bg-red-100 dark:hover:bg-red-900/20 rounded-none transition-colors"
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                  </div>
                ))}
              </div>
              <Button
                type="button"
                onClick={() => {
                  setEditingField({
                    ...editingField,
                    enum: [...(editingField.enum || []), ''],
                  })
                }}
                size="sm"
                variant="primary"
              >
                <Plus className="w-3 h-3" />
                Add Value
              </Button>
            </div>
          )}

          {/* Number Constraints - for number/integer types */}
          {(editingField.type === 'number' || editingField.type === 'integer') && (
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-foreground/90 mb-2">
                  Minimum (optional)
                </label>
                <Input
                  type="number"
                  value={editingField.minimum !== undefined ? editingField.minimum : ''}
                  onChange={(e) =>
                    setEditingField({
                      ...editingField,
                      minimum: e.target.value === '' ? undefined : Number(e.target.value),
                    })
                  }
                  placeholder="e.g., 0"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground/90 mb-2">
                  Maximum (optional)
                </label>
                <Input
                  type="number"
                  value={editingField.maximum !== undefined ? editingField.maximum : ''}
                  onChange={(e) =>
                    setEditingField({
                      ...editingField,
                      maximum: e.target.value === '' ? undefined : Number(e.target.value),
                    })
                  }
                  placeholder="e.g., 100"
                />
              </div>
            </div>
          )}

          {/* Format - for string types */}
          {editingField.type === 'string' && (
            <div>
              <label className="block text-sm font-medium text-foreground/90 mb-2">
                Format (optional)
              </label>
              <Select
                value={editingField.format || ''}
                onChange={(e) =>
                  setEditingField({
                    ...editingField,
                    format: e.target.value || undefined,
                  })
                }
              >
                <option value="">None</option>
                {STRING_FORMATS.map((f) => (
                  <option key={f.value} value={f.value}>
                    {f.label}
                  </option>
                ))}
              </Select>
            </div>
          )}

          {/* Pattern - for string types */}
          {editingField.type === 'string' && (
            <div>
              <label className="block text-sm font-medium text-foreground/90 mb-2">
                Regex Pattern (optional)
              </label>
              <Input
                type="text"
                value={editingField.pattern || ''}
                onChange={(e) =>
                  setEditingField({
                    ...editingField,
                    pattern: e.target.value || undefined,
                  })
                }
                placeholder="e.g., ^[A-Z]{2}\\d{3}$"
                helperText="For custom validation patterns. Examples: email regex, zipcode format, etc."
              />
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-3 pt-4 border-t border-border flex-col sm:flex-row">
            <Button
              onClick={saveField}
              className="flex-1 w-full sm:w-auto"
            >
              Save Field
            </Button>
            <Button
              onClick={() => setEditingField(null)}
              variant="outline"
              className="flex-1 w-full sm:w-auto"
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
      </Modal>
    </>
  )
}
