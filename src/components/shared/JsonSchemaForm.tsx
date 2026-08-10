import { useMemo } from 'react'
import { SingleSelectCombobox } from '@/components/ui/combobox'

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

/** allOf if/then: when value[field] === const, then.required applies. */
export interface SchemaConditionalRequired {
  if?: { properties?: Record<string, { const?: unknown }> }
  then?: { required?: string[] }
}

export interface JsonSchema {
  type?: string
  properties?: Record<string, FieldSchema>
  required?: string[]
  allOf?: SchemaConditionalRequired[]
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
  if (schema.type === 'string' && schema.format === 'email') return 'email'
  if (schema.type === 'string' && schema.format === 'uri') return 'url'
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

/** Get conditionally required field names based on current value (allOf if/then with single-property const). */
function getConditionalRequired(schema: JsonSchema | undefined, value: Record<string, unknown>): string[] {
  const out: string[] = []
  const allOf = schema?.allOf
  if (!Array.isArray(allOf)) return out
  for (const block of allOf) {
    const ifProps = block.if?.properties
    const thenRequired = block.then?.required
    if (!ifProps || typeof ifProps !== 'object' || !Array.isArray(thenRequired) || thenRequired.length === 0) continue
    const keys = Object.keys(ifProps)
    if (keys.length !== 1) continue
    const triggerKey = keys[0]
    const constraint = ifProps[triggerKey]
    const expected = constraint?.const
    const actual = value[triggerKey]
    const match = actual === expected || (expected !== undefined && String(actual) === String(expected))
    if (match) out.push(...thenRequired)
  }
  return out
}

/** Base required + conditionally required from allOf given current value. */
export function getEffectiveRequiredFields(schema: JsonSchema | undefined, value: Record<string, unknown>): string[] {
  const base = schema?.required ?? []
  const conditional = getConditionalRequired(schema, value)
  return [...new Set([...base, ...conditional])]
}

/** Validate value against schema (required + conditional required). Returns field name -> error message. */
export function validateJsonSchema(
  schema: JsonSchema | undefined,
  value: Record<string, unknown>,
): Record<string, string> {
  const errors: Record<string, string> = {}
  if (!schema?.properties) return errors
  const required = getEffectiveRequiredFields(schema, value)
  for (const fieldName of required) {
    const v = value[fieldName]
    const isEmpty = v === undefined || v === null || (typeof v === 'string' && v.trim() === '')
    if (isEmpty) errors[fieldName] = 'Required'
  }
  return errors
}

function isRequired(
  schema: JsonSchema | undefined,
  fieldName: string,
  requiredFields: string[],
): boolean {
  return requiredFields.includes(fieldName)
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
    return getEffectiveRequiredFields(schema, value)
  }, [schema, value])

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
            {fieldType === 'checkbox' ? (
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={Boolean(fieldValue)}
                  onChange={(e) => handleChange(fieldName, e.target.checked)}
                  className="w-4 h-4 rounded-none border-input"
                />
                <span className="text-sm font-medium">
                  {description || fieldName}
                  {isReq && <span className="text-red-500 ml-1">*</span>}
                </span>
              </label>
            ) : (
              <>
                <label className="block text-sm font-medium mb-1">
                  {description || fieldName}
                  {isReq && <span className="text-red-500 ml-1">*</span>}
                </label>
                {fieldSchema.enum ? (
              <SingleSelectCombobox
                value={toDisplayValue(fieldValue)}
                onValueChange={(v) => handleChange(fieldName, v)}
                options={[
                  { value: '', label: `Select ${fieldName}` },
                  ...fieldSchema.enum.map((opt: unknown) => {
                    const s = String(opt)
                    return { value: s, label: s }
                  }),
                ]}
                placeholder={`Select ${fieldName}`}
                error={fieldError}
                className={inputClassName(Boolean(fieldError))}
              />
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
              </>
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
