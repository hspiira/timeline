import { useState, useMemo } from 'react'
import { Plus, Trash2, Code, ListPlus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const FIELD_TYPES = [
  { value: 'string', label: 'Text' },
  { value: 'number', label: 'Number' },
  { value: 'integer', label: 'Whole number' },
  { value: 'boolean', label: 'Yes / No' },
  { value: 'date', label: 'Date' },
  { value: 'date-time', label: 'Date & time' },
] as const

type FieldTypeValue = (typeof FIELD_TYPES)[number]['value']

interface SchemaField {
  key: string
  type: FieldTypeValue
  title: string
  required: boolean
}

function parseSchemaFromJson(json: string): { properties: Record<string, unknown>; required: string[] } {
  const trimmed = json.trim()
  if (!trimmed) return { properties: {}, required: [] }
  try {
    const v = JSON.parse(trimmed)
    if (typeof v !== 'object' || v === null) return { properties: {}, required: [] }
    const properties = (v.properties && typeof v.properties === 'object') ? v.properties as Record<string, unknown> : {}
    const required = Array.isArray(v.required) ? (v.required as string[]) : []
    return { properties, required }
  } catch {
    return { properties: {}, required: [] }
  }
}

function schemaFieldToProperty(type: FieldTypeValue): Record<string, unknown> {
  if (type === 'date') return { type: 'string', format: 'date' }
  if (type === 'date-time') return { type: 'string', format: 'date-time' }
  return { type }
}

function propertyToSchemaField(key: string, prop: Record<string, unknown>, required: string[]): SchemaField {
  const type = (prop.type as string) === 'string' && (prop.format as string) === 'date'
    ? 'date'
    : (prop.type as string) === 'string' && (prop.format as string) === 'date-time'
      ? 'date-time'
      : ((prop.type as string) || 'string') as FieldTypeValue
  return {
    key,
    type: ['string', 'number', 'integer', 'boolean', 'date', 'date-time'].includes(type) ? type : 'string',
    title: (prop.title as string) || '',
    required: required.includes(key),
  }
}

function fieldsToSchema(fields: SchemaField[]): Record<string, unknown> {
  const properties: Record<string, unknown> = {}
  const required: string[] = []
  for (const f of fields) {
    const key = (f.key || '').trim()
    if (!key) continue
    const prop: Record<string, unknown> = schemaFieldToProperty(f.type)
    if (f.title) prop.title = f.title
    properties[key] = prop
    if (f.required) required.push(key)
  }
  return { type: 'object', properties, required: required.length ? required : undefined }
}

function schemaToFields(properties: Record<string, unknown>, required: string[]): SchemaField[] {
  return Object.entries(properties).map(([key, prop]) =>
    propertyToSchemaField(key, (prop as Record<string, unknown>) || {}, required)
  )
}

interface AttributeSchemaBuilderProps {
  value: string
  onChange: (json: string) => void
  disabled?: boolean
  /** Placeholder when JSON is empty */
  placeholder?: string
}

export function AttributeSchemaBuilder({
  value,
  onChange,
  disabled = false,
  placeholder = '{"type":"object","properties":{}}',
}: AttributeSchemaBuilderProps) {
  const [mode, setMode] = useState<'visual' | 'json'>('visual')
  const [jsonError, setJsonError] = useState<string | null>(null)

  const { properties, required } = useMemo(() => parseSchemaFromJson(value), [value])

  const fields = useMemo(
    () => (Object.keys(properties).length ? schemaToFields(properties, required) : []),
    [properties, required]
  )

  const updateFields = (newFields: SchemaField[]) => {
    const schema = fieldsToSchema(newFields)
    onChange(JSON.stringify(schema, null, 2))
  }

  const addField = () => {
    const base = 'field_'
    let n = 1
    while (fields.some((f) => f.key === base + n)) n++
    updateFields([...fields, { key: base + n, type: 'string', title: '', required: false }])
  }

  const updateField = (index: number, patch: Partial<SchemaField>) => {
    const next = [...fields]
    next[index] = { ...next[index], ...patch }
    updateFields(next)
  }

  const removeField = (index: number) => {
    updateFields(fields.filter((_, i) => i !== index))
  }

  const handleJsonChange = (raw: string) => {
    onChange(raw)
    if (raw.trim()) {
      try {
        JSON.parse(raw)
        setJsonError(null)
      } catch {
        setJsonError('Invalid JSON')
      }
    } else {
      setJsonError(null)
    }
  }

  const switchToVisual = () => {
    setJsonError(null)
    setMode('visual')
  }

  const switchToJson = () => {
    setMode('json')
  }

  return (
    <div className="rounded-lg bg-muted/5 overflow-hidden">
      <div className="flex items-center justify-between gap-2 px-2.5 py-1.5 bg-muted/10">
        <div className="flex gap-px rounded-md overflow-hidden bg-border/30">
          <button
            type="button"
            onClick={switchToVisual}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors rounded-md',
              mode === 'visual'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/30'
            )}
          >
            <ListPlus className="w-3.5 h-3.5" />
            Add fields
          </button>
          <button
            type="button"
            onClick={switchToJson}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors rounded-md',
              mode === 'json'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/30'
            )}
          >
            <Code className="w-3.5 h-3.5" />
            JSON
          </button>
        </div>
        {mode === 'visual' && (
          <Button type="button" variant="ghost" size="sm" onClick={addField} disabled={disabled}>
            <Plus className="w-3.5 h-3.5" />
            Add field
          </Button>
        )}
      </div>

      {mode === 'visual' && (
        <div className="p-2.5 space-y-0.5 max-h-64 overflow-y-auto">
          {fields.length === 0 && (
            <p className="text-xs text-muted-foreground py-4 text-center">
              No fields yet. Add fields to define custom attributes for this subject type.
            </p>
          )}
          {fields.map((field, index) => (
            <div
              key={index}
              className="flex flex-wrap items-center gap-2 py-1 px-2 rounded-md bg-background/60 hover:bg-background/80"
            >
              <input
                type="text"
                value={field.key}
                onChange={(e) => updateField(index, { key: e.target.value })}
                placeholder="Field name"
                disabled={disabled}
                className="w-28 min-w-0 px-2 py-1.5 text-xs font-mono bg-background/80 border border-border/50 rounded focus:border-border focus:ring-1 focus:ring-border/50 focus:outline-none"
              />
              <select
                value={field.type}
                onChange={(e) => updateField(index, { type: e.target.value as FieldTypeValue })}
                disabled={disabled}
                className="px-2 py-1.5 text-xs bg-background/80 border border-border/50 rounded focus:border-border focus:ring-1 focus:ring-border/50 focus:outline-none"
              >
                {FIELD_TYPES.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <input
                type="text"
                value={field.title}
                onChange={(e) => updateField(index, { title: e.target.value })}
                placeholder="Label (optional)"
                disabled={disabled}
                className="flex-1 min-w-0 max-w-32 px-2 py-1.5 text-xs bg-background/80 border border-border/50 rounded focus:border-border focus:ring-1 focus:ring-border/50 focus:outline-none"
              />
              <label className="flex items-center gap-1 text-xs text-muted-foreground whitespace-nowrap">
                <input
                  type="checkbox"
                  checked={field.required}
                  onChange={(e) => updateField(index, { required: e.target.checked })}
                  disabled={disabled}
                  className="rounded border-input"
                />
                Required
              </label>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => removeField(index)}
                disabled={disabled}
                className="text-muted-foreground hover:text-destructive h-7 w-7 p-0"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </Button>
            </div>
          ))}
        </div>
      )}

      {mode === 'json' && (
        <div className="p-2.5">
          <textarea
            value={value}
            onChange={(e) => handleJsonChange(e.target.value)}
            disabled={disabled}
            placeholder={placeholder}
            rows={14}
            className={cn(
              'w-full px-2.5 py-2 text-[11px] font-mono leading-relaxed bg-background/80 rounded resize-y min-h-[240px] focus:outline-none focus:ring-1 focus:ring-border/50',
              jsonError ? 'border border-red-400' : 'border border-border/40 focus:border-border'
            )}
          />
          {jsonError && (
            <p className="text-xs text-destructive mt-1">{jsonError}</p>
          )}
        </div>
      )}
    </div>
  )
}
