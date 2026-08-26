import { Code, Filter, ListPlus, Plus, Trash2 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const FIELD_TYPES = [
  { value: 'string', label: 'Text' },
  { value: 'number', label: 'Number' },
  { value: 'integer', label: 'Whole number' },
  { value: 'boolean', label: 'Yes / No' },
  { value: 'date', label: 'Date' },
  { value: 'date-time', label: 'Date & time' },
  { value: 'email', label: 'Email' },
  { value: 'uri', label: 'URL' },
  { value: 'enum', label: 'Enum (dropdown)' },
] as const

type FieldTypeValue = (typeof FIELD_TYPES)[number]['value']

interface SchemaField {
  key: string
  type: FieldTypeValue
  title: string
  /** Optional description (shown as hint in subject form). */
  description?: string
  required: boolean
  /** For type 'enum': allowed values (e.g. ["active", "inactive"]). */
  enumValues?: string[]
}

/** Visual rule: when triggerField equals triggerValue, require requiredFields. */
export interface ConditionalRule {
  triggerField: string
  triggerValue: string
  requiredFields: string[]
}

/** allOf block shape used by JsonSchemaForm (if/then). */
interface AllOfBlock {
  if?: { properties?: Record<string, { const?: unknown }> }
  then?: { required?: string[] }
}

function parseSchemaFromJson(json: string): {
  properties: Record<string, unknown>
  required: string[]
  allOf: AllOfBlock[] | undefined
} {
  const trimmed = json.trim()
  if (!trimmed) return { properties: {}, required: [], allOf: undefined }
  try {
    const v = JSON.parse(trimmed)
    if (typeof v !== 'object' || v === null)
      return { properties: {}, required: [], allOf: undefined }
    const properties =
      v.properties && typeof v.properties === 'object'
        ? (v.properties as Record<string, unknown>)
        : {}
    const required = Array.isArray(v.required) ? (v.required as string[]) : []
    const allOf = Array.isArray(v.allOf) ? (v.allOf as AllOfBlock[]) : undefined
    return { properties, required, allOf }
  } catch {
    return { properties: {}, required: [], allOf: undefined }
  }
}

function parseAllOfToRules(allOf: AllOfBlock[] | undefined): ConditionalRule[] {
  if (!Array.isArray(allOf)) return []
  const rules: ConditionalRule[] = []
  for (const block of allOf) {
    const ifProps = block.if?.properties
    const thenRequired = block.then?.required
    if (
      !ifProps ||
      typeof ifProps !== 'object' ||
      !Array.isArray(thenRequired) ||
      thenRequired.length === 0
    )
      continue
    const keys = Object.keys(ifProps)
    if (keys.length !== 1) continue
    const triggerField = keys[0]
    const constraint = ifProps[triggerField]
    const triggerValue = constraint?.const != null ? String(constraint.const) : ''
    rules.push({ triggerField, triggerValue, requiredFields: [...thenRequired] })
  }
  return rules
}

function rulesToAllOf(rules: ConditionalRule[]): AllOfBlock[] | undefined {
  const filtered = rules.filter((r) => r.triggerField.trim())
  if (filtered.length === 0) return undefined
  return filtered.map((r) => ({
    if: { properties: { [r.triggerField]: { const: r.triggerValue } } },
    // biome-ignore lint/suspicious/noThenProperty: JSON Schema's if/then keyword.
    then: { required: r.requiredFields },
  }))
}

function schemaFieldToProperty(field: SchemaField): Record<string, unknown> {
  const { type } = field
  let prop: Record<string, unknown>
  if (type === 'date') prop = { type: 'string', format: 'date' }
  else if (type === 'date-time') prop = { type: 'string', format: 'date-time' }
  else if (type === 'email') prop = { type: 'string', format: 'email' }
  else if (type === 'uri') prop = { type: 'string', format: 'uri' }
  else if (type === 'enum') {
    const enumValues = field.enumValues?.filter(Boolean) ?? []
    prop = enumValues.length > 0 ? { type: 'string', enum: enumValues } : { type: 'string' }
  } else {
    prop = { type }
  }
  if (field.description) prop.description = field.description
  return prop
}

const VALID_FIELD_TYPES: string[] = [
  'string',
  'number',
  'integer',
  'boolean',
  'date',
  'date-time',
  'email',
  'uri',
  'enum',
]

function propertyToSchemaField(
  key: string,
  prop: Record<string, unknown>,
  required: string[],
): SchemaField {
  const rawType = prop.type as string
  const format = prop.format as string
  const enumArr = prop.enum as unknown[] | undefined

  let type: FieldTypeValue = 'string'
  let enumValues: string[] | undefined

  if (Array.isArray(enumArr) && enumArr.length > 0) {
    type = 'enum'
    enumValues = enumArr.map((v) => String(v))
  } else if (rawType === 'string' && format === 'date') {
    type = 'date'
  } else if (rawType === 'string' && format === 'date-time') {
    type = 'date-time'
  } else if (rawType === 'string' && format === 'email') {
    type = 'email'
  } else if (rawType === 'string' && format === 'uri') {
    type = 'uri'
  } else if (VALID_FIELD_TYPES.includes(rawType)) {
    type = rawType as FieldTypeValue
  }

  return {
    key,
    type,
    title: (prop.title as string) || '',
    description: (prop.description as string) || undefined,
    required: required.includes(key),
    ...(enumValues && { enumValues }),
  }
}

function fieldsToSchema(fields: SchemaField[]): Record<string, unknown> {
  const properties: Record<string, unknown> = {}
  const required: string[] = []
  for (const f of fields) {
    const key = (f.key || '').trim()
    if (!key) continue
    const prop: Record<string, unknown> = schemaFieldToProperty(f)
    if (f.title) prop.title = f.title
    properties[key] = prop
    if (f.required) required.push(key)
  }
  return { type: 'object', properties, required: required.length ? required : undefined }
}

function schemaToFields(properties: Record<string, unknown>, required: string[]): SchemaField[] {
  return Object.entries(properties).map(([key, prop]) =>
    propertyToSchemaField(key, (prop as Record<string, unknown>) || {}, required),
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

  const { properties, required, allOf } = useMemo(() => parseSchemaFromJson(value), [value])

  const fields = useMemo(
    () => (Object.keys(properties).length ? schemaToFields(properties, required) : []),
    [properties, required],
  )

  const conditionalRules = useMemo(() => parseAllOfToRules(allOf), [allOf])

  const updateFields = (newFields: SchemaField[]) => {
    const schema = { ...fieldsToSchema(newFields), allOf: rulesToAllOf(conditionalRules) }
    onChange(JSON.stringify(schema, null, 2))
  }

  const updateConditionalRules = (newRules: ConditionalRule[]) => {
    const schema: Record<string, unknown> = {
      type: 'object',
      properties,
      ...(required.length ? { required } : {}),
      ...(rulesToAllOf(newRules) && { allOf: rulesToAllOf(newRules) }),
    }
    onChange(JSON.stringify(schema, null, 2))
  }

  const addField = () => {
    const base = 'field_'
    let n = 1
    while (fields.some((f) => f.key === base + n)) n++
    updateFields([...fields, { key: base + n, type: 'string', title: '', required: false }])
  }

  const setEnumValues = (index: number, raw: string) => {
    const values = raw
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    updateField(index, { enumValues: values })
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
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/30',
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
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/30',
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
              className="flex flex-wrap items-center gap-2 py-1.5 px-2 rounded-md bg-background/60 hover:bg-background/80"
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
                onChange={(e) => {
                  const v = e.target.value as FieldTypeValue
                  updateField(index, {
                    type: v,
                    ...(v === 'enum' && !field.enumValues?.length && { enumValues: [] }),
                  })
                }}
                disabled={disabled}
                className="px-2 py-1.5 text-xs bg-background/80 border border-border/50 rounded focus:border-border focus:ring-1 focus:ring-border/50 focus:outline-none"
              >
                {FIELD_TYPES.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              {field.type === 'enum' && (
                <input
                  type="text"
                  value={(field.enumValues ?? []).join(', ')}
                  onChange={(e) => setEnumValues(index, e.target.value)}
                  placeholder="Values: active, inactive"
                  disabled={disabled}
                  className="min-w-[140px] flex-1 max-w-48 px-2 py-1.5 text-xs font-mono bg-background/80 border border-border/50 rounded focus:border-border focus:ring-1 focus:ring-border/50 focus:outline-none"
                  title="Comma-separated enum values"
                />
              )}
              <input
                type="text"
                value={field.title}
                onChange={(e) => updateField(index, { title: e.target.value })}
                placeholder="Label (optional)"
                disabled={disabled}
                className="flex-1 min-w-0 max-w-32 px-2 py-1.5 text-xs bg-background/80 border border-border/50 rounded focus:border-border focus:ring-1 focus:ring-border/50 focus:outline-none"
              />
              <input
                type="text"
                value={field.description ?? ''}
                onChange={(e) => updateField(index, { description: e.target.value || undefined })}
                placeholder="Hint (optional)"
                disabled={disabled}
                className="min-w-0 max-w-28 px-2 py-1.5 text-xs bg-background/80 border border-border/50 rounded focus:border-border focus:ring-1 focus:ring-border/50 focus:outline-none"
                title="Description shown as hint in subject form"
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

          {fields.length >= 1 && (
            <div className="mt-3 pt-3 border-t border-border/50 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <Filter className="w-3.5 h-3.5" />
                Conditional required
              </div>
              <p className="text-[11px] text-muted-foreground">
                When a field has a specific value, require other fields (e.g. when type =
                &quot;individual&quot;, require full_name). Add at least 2 fields to add a rule.
              </p>
              {conditionalRules.map((rule, ruleIndex) => {
                const triggerFieldDef = fields.find((f) => f.key === rule.triggerField)
                const otherFieldKeys = fields
                  .filter((f) => f.key !== rule.triggerField)
                  .map((f) => f.key)
                return (
                  <div
                    key={ruleIndex}
                    className="flex flex-wrap items-center gap-2 py-1.5 px-2 rounded-md bg-muted/30"
                  >
                    <span className="text-xs text-muted-foreground">When</span>
                    <select
                      value={rule.triggerField}
                      onChange={(e) => {
                        const next = [...conditionalRules]
                        next[ruleIndex] = {
                          ...next[ruleIndex],
                          triggerField: e.target.value,
                          triggerValue: '',
                        }
                        updateConditionalRules(next)
                      }}
                      disabled={disabled}
                      className="px-2 py-1.5 text-xs font-mono bg-background/80 border border-border/50 rounded focus:outline-none focus:ring-1 focus:ring-border/50 min-w-[100px]"
                    >
                      {fields.map((f) => (
                        <option key={f.key} value={f.key}>
                          {f.key}
                        </option>
                      ))}
                    </select>
                    <span className="text-xs text-muted-foreground">equals</span>
                    {triggerFieldDef?.type === 'enum' &&
                    (triggerFieldDef.enumValues?.length ?? 0) > 0 ? (
                      <select
                        value={rule.triggerValue}
                        onChange={(e) => {
                          const next = [...conditionalRules]
                          next[ruleIndex] = { ...next[ruleIndex], triggerValue: e.target.value }
                          updateConditionalRules(next)
                        }}
                        disabled={disabled}
                        className="px-2 py-1.5 text-xs font-mono bg-background/80 border border-border/50 rounded focus:outline-none focus:ring-1 focus:ring-border/50 min-w-[100px]"
                      >
                        {(triggerFieldDef.enumValues ?? []).map((v) => (
                          <option key={v} value={v}>
                            {v}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={rule.triggerValue}
                        onChange={(e) => {
                          const next = [...conditionalRules]
                          next[ruleIndex] = { ...next[ruleIndex], triggerValue: e.target.value }
                          updateConditionalRules(next)
                        }}
                        placeholder="value"
                        disabled={disabled}
                        className="w-24 min-w-0 px-2 py-1.5 text-xs font-mono bg-background/80 border border-border/50 rounded focus:outline-none focus:ring-1 focus:ring-border/50"
                      />
                    )}
                    <span className="text-xs text-muted-foreground">require</span>
                    <div className="flex flex-wrap items-center gap-1.5">
                      {otherFieldKeys.map((key) => (
                        <label key={key} className="flex items-center gap-1 text-xs cursor-pointer">
                          <input
                            type="checkbox"
                            checked={rule.requiredFields.includes(key)}
                            onChange={(e) => {
                              const next = [...conditionalRules]
                              const current = next[ruleIndex].requiredFields
                              next[ruleIndex] = {
                                ...next[ruleIndex],
                                requiredFields: e.target.checked
                                  ? [...current, key]
                                  : current.filter((k) => k !== key),
                              }
                              updateConditionalRules(next)
                            }}
                            disabled={disabled}
                            className="rounded border-input"
                          />
                          {key}
                        </label>
                      ))}
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        updateConditionalRules(conditionalRules.filter((_, i) => i !== ruleIndex))
                      }
                      disabled={disabled}
                      className="text-muted-foreground hover:text-destructive h-7 w-7 p-0"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                )
              })}
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() =>
                  updateConditionalRules([
                    ...conditionalRules,
                    { triggerField: fields[0]?.key ?? '', triggerValue: '', requiredFields: [] },
                  ])
                }
                disabled={disabled || fields.length < 2}
                className="text-xs h-7"
              >
                <Plus className="w-3.5 h-3.5 mr-1" />
                Add rule
              </Button>
            </div>
          )}
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
              jsonError ? 'border border-red-400' : 'border border-border/40 focus:border-border',
            )}
          />
          {jsonError && <p className="text-xs text-destructive mt-1">{jsonError}</p>}
        </div>
      )}
    </div>
  )
}
