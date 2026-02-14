import { useMemo } from 'react'

export interface JsonSchemaFormProps {
  schema?: Record<string, any>
  value: Record<string, any>
  onChange: (value: Record<string, any>) => void
  errors?: Record<string, string>
}

function getFieldType(schema: any): string {
  if (schema.type === 'string') return 'text'
  if (schema.type === 'number') return 'number'
  if (schema.type === 'integer') return 'number'
  if (schema.type === 'boolean') return 'checkbox'
  return 'text'
}

function isRequired(schema: any, fieldName: string, requiredFields?: string[]): boolean {
  return requiredFields?.includes(fieldName) ?? schema.required?.includes(fieldName) ?? false
}

export function JsonSchemaForm({
  schema,
  value,
  onChange,
  errors = {},
}: JsonSchemaFormProps) {
  const properties = useMemo(() => {
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

  const handleChange = (fieldName: string, fieldValue: any) => {
    onChange({
      ...value,
      [fieldName]: fieldValue,
    })
  }

  return (
    <div className="space-y-4">
      {Object.entries(properties).map(([fieldName, fieldSchema]: [string, any]) => {
        const isReq = isRequired(schema, fieldName, requiredFields)
        const fieldType = getFieldType(fieldSchema)
        const fieldValue = value[fieldName] ?? ''
        const fieldError = errors[fieldName]
        const description = fieldSchema.description || fieldSchema.title

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
                value={fieldValue}
                onChange={(e) => handleChange(fieldName, e.target.value)}
                className={`w-full px-3 py-2 bg-background border rounded-none text-sm ${
                  fieldError ? 'border-red-500' : 'border-input'
                }`}
                required={isReq}
              >
                <option value="">Select {fieldName}</option>
                {fieldSchema.enum.map((opt: any) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            ) : fieldSchema.type === 'number' || fieldSchema.type === 'integer' ? (
              <input
                type="number"
                value={fieldValue}
                onChange={(e) => handleChange(fieldName, parseFloat(e.target.value) || '')}
                placeholder={fieldSchema.default ? `(default: ${fieldSchema.default})` : ''}
                className={`w-full px-3 py-2 bg-background border rounded-none text-sm ${
                  fieldError ? 'border-red-500' : 'border-input'
                }`}
                required={isReq}
                step={fieldSchema.type === 'integer' ? '1' : 'any'}
              />
            ) : (
              <input
                type={fieldType}
                value={fieldValue}
                onChange={(e) => handleChange(fieldName, e.target.value)}
                placeholder={fieldSchema.default ? `(default: ${fieldSchema.default})` : ''}
                className={`w-full px-3 py-2 bg-background border rounded-none text-sm ${
                  fieldError ? 'border-red-500' : 'border-input'
                }`}
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
