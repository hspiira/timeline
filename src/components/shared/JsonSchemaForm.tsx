import { useMemo } from 'react'

export interface FieldSchema {
  type?: 'string' | 'number' | 'integer' | 'boolean' | 'object' | 'array'
  format?: string
  enum?: unknown[]
  description?: string
  title?: string
  default?: unknown
  minimum?: number
  maximum?: number
  pattern?: string
}

export interface JsonSchema {
  type?: string
  properties?: Record<string, FieldSchema>
  required?: string[]
}

export interface JsonSchemaFormProps {
  schema?: JsonSchema
  value: Record<string, unknown>
  onChange: (value: Record<string, unknown>) => void
  errors?: Record<string, string>
}

function getFieldType(schema: FieldSchema): string {
  if (schema.type === 'string' && schema.format === 'date') return 'date'
  if (schema.type === 'string' && schema.format === 'date-time') return 'datetime-local'
  if (schema.type === 'string') return 'text'
  if (schema.type === 'number') return 'number'
  if (schema.type === 'integer') return 'number'
  if (schema.type === 'boolean') return 'checkbox'
  return 'text'
}

/** Normalize value for <input type="date"> (YYYY-MM-DD). */
function toDateInputValue(value: unknown): string {
  if (value == null || value === '') return ''
  const s = String(value)
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10)
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return ''
  return d.toISOString().slice(0, 10)
}

/** Normalize value for <input type="datetime-local"> (YYYY-MM-DDTHH:mm in local time). */
function toDatetimeLocalInputValue(value: unknown): string {
  if (value == null || value === '') return ''
  const d = new Date(String(value))
  if (Number.isNaN(d.getTime())) return ''
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${day}T${h}:${min}`
}

function isRequired(
  schema: JsonSchema | undefined,
  fieldName: string,
  requiredFields?: string[],
): boolean {
  return requiredFields?.includes(fieldName) ?? schema?.required?.includes(fieldName) ?? false
}

/** Single place for input styling (DRY). */
function inputClassName(hasError: boolean): string {
  return `w-full px-3 py-2 bg-background border rounded-none text-sm ${
    hasError ? 'border-red-500' : 'border-input'
  }`
}

/** Normalize value for display in text-like inputs (empty → ''). */
function toDisplayValue(value: unknown): string {
  return value === undefined || value === null ? '' : String(value)
}

export function JsonSchemaForm({
  schema,
  value,
  onChange,
  errors = {},
}: JsonSchemaFormProps) {
  const properties = useMemo((): Record<string, FieldSchema> => {
    if (!schema?.properties) return {}
    return schema.properties
  }, [schema])

  const requiredFields = useMemo(() => {
    return schema?.required ?? []
  }, [schema])

  if (!schema || !Object.keys(properties).length) {
    return (
      <div className="text-sm text-muted-foreground italic">
        No schema available. Provide payload as JSON.
      </div>
    )
  }

  const handleChange = (fieldName: string, fieldValue: unknown) => {
    onChange({
      ...value,
      [fieldName]: fieldValue,
    })
  }

  return (
    <div className="space-y-4">
      {Object.entries(properties).map(([fieldName, fieldSchema]) => {
        const isReq = isRequired(schema, fieldName, requiredFields)
        const fieldType = getFieldType(fieldSchema)
        const fieldValue = value[fieldName] ?? ''
        const fieldError = errors[fieldName]
        const description = fieldSchema.description ?? fieldSchema.title

        return (
          <div key={fieldName}>
            <label className="block text-sm font-medium mb-1">
              {description || fieldName}
              {isReq && <span className="text-red-500 ml-1">*</span>}
            </label>

            {fieldType === 'checkbox' ? (
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={Boolean(fieldValue)}
                  onChange={(e) => handleChange(fieldName, e.target.checked)}
                  className="w-4 h-4 rounded-none border-input"
                />
              </div>
            ) : fieldSchema.enum ? (
              <select
                value={toDisplayValue(fieldValue)}
                onChange={(e) => handleChange(fieldName, e.target.value)}
                className={inputClassName(Boolean(fieldError))}
                required={isReq}
              >
                <option value="">Select {fieldName}</option>
                {fieldSchema.enum.map((opt: unknown) => (
                  <option key={String(opt)} value={String(opt)}>
                    {String(opt)}
                  </option>
                ))}
              </select>
            ) : fieldSchema.type === 'number' || fieldSchema.type === 'integer' ? (
              <input
                type="number"
                value={
                  fieldValue === undefined || fieldValue === ''
                    ? ''
                    : typeof fieldValue === 'number'
                      ? fieldValue
                      : Number(fieldValue) || ''
                }
                onChange={(e) => {
                  const val = e.target.value
                  handleChange(fieldName, val === '' ? undefined : parseFloat(val))
                }}
                placeholder={fieldSchema.default ? `(default: ${fieldSchema.default})` : ''}
                className={inputClassName(Boolean(fieldError))}
                required={isReq}
                step={fieldSchema.type === 'integer' ? '1' : 'any'}
              />
            ) : fieldType === 'date' ? (
              <input
                type="date"
                value={toDateInputValue(fieldValue)}
                onChange={(e) => handleChange(fieldName, e.target.value || undefined)}
                className={inputClassName(Boolean(fieldError))}
                required={isReq}
              />
            ) : fieldType === 'datetime-local' ? (
              <input
                type="datetime-local"
                value={toDatetimeLocalInputValue(fieldValue)}
                onChange={(e) =>
                  handleChange(
                    fieldName,
                    e.target.value ? new Date(e.target.value).toISOString() : undefined,
                  )
                }
                className={inputClassName(Boolean(fieldError))}
                required={isReq}
              />
            ) : (
              <input
                type={fieldType}
                value={toDisplayValue(fieldValue)}
                onChange={(e) => handleChange(fieldName, e.target.value)}
                placeholder={fieldSchema.default ? `(default: ${fieldSchema.default})` : ''}
                className={inputClassName(Boolean(fieldError))}
                required={isReq}
              />
            )}

            {fieldError && <p className="text-xs text-red-500 mt-1">{fieldError}</p>}
            {fieldSchema.description && !fieldError && (
              <p className="text-xs text-muted-foreground mt-1">{fieldSchema.description}</p>
            )}
          </div>
        )
      })}
    </div>
  )
}
