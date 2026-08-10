import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useState, useMemo, useEffect } from 'react'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { useQuery } from '@tanstack/react-query'
import { timelineApi } from '@/lib/api-client'
import { useToast } from '@/hooks/useToast'
import { getApiErrorDisplay } from '@/lib/api-utils'
import { ArrowLeft } from 'lucide-react'
import { LoadingIcon } from '@/components/ui/icons'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { SingleSelectCombobox } from '@/components/ui/combobox'
import { Breadcrumbs } from '@/components/ui/Breadcrumbs'
import SubjectSelector from '@/components/subjects/SubjectSelector'

export const Route = createFileRoute('/flows/create')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  component: CreateFlowPage,
})

/** Extract placeholder keys from template string, e.g. "{year}-{month}-{name}" → ["year", "month", "name"] */
function parsePlaceholdersFromTemplate(templateString: string): string[] {
  const matches = templateString.match(/\{(\w+)\}/g) ?? []
  return [...new Set(matches.map((m) => m.slice(1, -1)))]
}

/** Build flow name from template by replacing {key} with values from record */
function buildNameFromTemplate(
  templateString: string,
  values: Record<string, string>
): string {
  return templateString.replace(/\{(\w+)\}/g, (_, key) => values[key] ?? '')
}

/** Human-friendly label for a placeholder key (fallback when no subject type schema). */
const PLACEHOLDER_LABELS: Record<string, string> = {
  year: 'Year',
  month: 'Month',
  day: 'Day',
  name: 'Name',
  client_name: 'Client name',
}

function placeholderLabel(key: string): string {
  return PLACEHOLDER_LABELS[key] ?? key.replace(/_/g, ' ')
}

/** Placeholder metadata derived from subject type schema (label + optional enum options). */
export type PlaceholderOption = { label: string; enum?: string[] }

/** Build placeholder key -> { label, enum? } from subject type schema. Only includes keys that appear in placeholderKeys. */
function placeholderOptionsFromSchema(
  schema: { properties?: Record<string, { title?: string; enum?: unknown[] }> } | null | undefined,
  placeholderKeys: string[]
): Map<string, PlaceholderOption> {
  const map = new Map<string, PlaceholderOption>()
  const props = schema?.properties && typeof schema.properties === 'object' ? schema.properties : {}
  for (const key of placeholderKeys) {
    const prop = props[key]
    const label =
      (prop && typeof prop === 'object' && typeof prop.title === 'string' && prop.title.trim())
        ? prop.title.trim()
        : placeholderLabel(key)
    const enumArr = Array.isArray(prop?.enum) ? prop.enum.map((v) => String(v)) : undefined
    map.set(key, enumArr?.length ? { label, enum: enumArr } : { label })
  }
  return map
}

function CreateFlowPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const [name, setName] = useState('')
  const [placeholderValues, setPlaceholderValues] = useState<
    Record<string, string>
  >({})
  const [workflowId, setWorkflowId] = useState('')
  const [subjectId, setSubjectId] = useState('')
  const [subjectTypeIdOptional, setSubjectTypeIdOptional] = useState('')
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const { data: workflows = [] } = useQuery({
    queryKey: ['workflows'],
    queryFn: async () => {
      const { data, error } = await timelineApi.workflows.list({ limit: 500 })
      if (error) return []
      return Array.isArray(data) ? data : []
    },
  })

  const { data: namingTemplates = [] } = useQuery({
    queryKey: ['naming-templates'],
    queryFn: async () => {
      const { data, error } = await timelineApi.namingTemplates.list({
        limit: 500,
      })
      if (error) return []
      return Array.isArray(data) ? data : []
    },
  })

  const { data: subjectTypesList = [] } = useQuery({
    queryKey: ['subject-types'],
    queryFn: async () => {
      const { data, error } = await timelineApi.subjectTypes.list({ limit: 500 })
      if (error) return []
      return Array.isArray(data) ? data : []
    },
  })

  const { data: selectedSubject } = useQuery({
    queryKey: ['subject', subjectId],
    queryFn: async () => {
      if (!subjectId) return null
      const { data } = await timelineApi.subjects.get(subjectId)
      return data ?? null
    },
    enabled: !!subjectId,
  })

  const subjectTypeIdForSchema = (() => {
    if (selectedSubject?.subject_type) {
      const st = subjectTypesList.find(
        (s: { type_name?: string; id?: string }) => s.type_name === selectedSubject.subject_type
      )
      return st?.id ?? null
    }
    return subjectTypeIdOptional || null
  })()

  const { data: subjectTypeSchema } = useQuery({
    queryKey: ['subject-type', subjectTypeIdForSchema],
    queryFn: async () => {
      if (!subjectTypeIdForSchema) return null
      const { data } = await timelineApi.subjectTypes.get(subjectTypeIdForSchema)
      return data?.schema ?? null
    },
    enabled: !!subjectTypeIdForSchema,
  })

  const templateForWorkflow = useMemo(() => {
    if (!workflowId) return null
    return namingTemplates.find(
      (t) => t.scope_type === 'flow' && t.scope_id === workflowId
    )
  }, [workflowId, namingTemplates])

  const placeholderKeys = useMemo(() => {
    if (!templateForWorkflow?.template_string) return []
    return parsePlaceholdersFromTemplate(templateForWorkflow.template_string)
  }, [templateForWorkflow])

  useEffect(() => {
    if (placeholderKeys.length === 0) setPlaceholderValues({})
  }, [placeholderKeys.length])

  const workflowOptions = [
    { value: '', label: 'No workflow' },
    ...workflows.map((w) => ({ value: w.id, label: w.name || w.id })),
  ]

  const useTemplateFields = templateForWorkflow && placeholderKeys.length > 0

  const placeholderOptionsMap = useMemo(
    () => placeholderOptionsFromSchema(subjectTypeSchema, placeholderKeys),
    [subjectTypeSchema, placeholderKeys]
  )

  const resolvedName = useMemo(() => {
    if (useTemplateFields && templateForWorkflow)
      return buildNameFromTemplate(
        templateForWorkflow.template_string,
        placeholderValues
      )
    return name.trim()
  }, [useTemplateFields, templateForWorkflow, placeholderValues, name])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitError(null)
    const nameToSubmit = useTemplateFields
      ? buildNameFromTemplate(
          templateForWorkflow!.template_string,
          placeholderValues
        )
      : name.trim()
    if (!nameToSubmit) {
      setSubmitError(
        useTemplateFields
          ? `Fill in all fields: ${placeholderKeys.map((k) => placeholderOptionsMap.get(k)?.label ?? placeholderLabel(k)).join(', ')}`
          : 'Name is required'
      )
      return
    }
    if (useTemplateFields) {
      const missing = placeholderKeys.filter(
        (k) => !(placeholderValues[k] ?? '').trim()
      )
      if (missing.length > 0) {
        const labels = missing.map((k) => placeholderOptionsMap.get(k)?.label ?? placeholderLabel(k))
        setSubmitError(`Required: ${labels.join(', ')}`)
        return
      }
    }
    setSubmitting(true)
    try {
      const { data, error, response } = await timelineApi.flows.create({
        name: nameToSubmit,
        workflow_id: workflowId || undefined,
        subject_ids: subjectId ? [subjectId] : undefined,
      })
      if (error) {
        const { message } = getApiErrorDisplay(
          { error, status: response?.status },
          'Failed to create flow'
        )
        setSubmitError(message)
        setSubmitting(false)
        return
      }
      if (data) {
        toast.success('Flow created', data.name)
        navigate({ to: '/flows/$flowId', params: { flowId: data.id } })
      }
    } catch (err) {
      setSubmitError('An unexpected error occurred')
      setSubmitting(false)
    }
  }

  return (
    <>
      <Breadcrumbs
        items={[
          { href: '/flows', label: 'Flows' },
          { label: 'New flow' },
        ]}
      />

      <div className="max-w-md">
        <h1 className="text-2xl font-bold text-foreground mb-4">
          Create flow
        </h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          {useTemplateFields ? (
            <>
              <p className="text-sm text-muted-foreground">
                This workflow uses a standard name format. Fill in each part; the flow name will be built automatically.
              </p>
              {!subjectId && (
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Subject type (optional)
                  </label>
                  <p className="text-xs text-muted-foreground mb-1.5">
                    Choose a subject type to use its attribute labels and dropdown options for the fields below.
                  </p>
                  <SingleSelectCombobox
                    value={subjectTypeIdOptional}
                    onValueChange={setSubjectTypeIdOptional}
                    options={[
                      { value: '', label: 'None — use default labels' },
                      ...subjectTypesList.map((st: { id: string; display_name?: string; type_name?: string }) => ({
                        value: st.id,
                        label: st.display_name || st.type_name || st.id,
                      })),
                    ]}
                    placeholder="Select subject type"
                    clearable
                    className="w-full"
                  />
                </div>
              )}
              {placeholderKeys.map((key) => {
                const opt = placeholderOptionsMap.get(key)
                const label = opt?.label ?? placeholderLabel(key)
                const enumOptions = opt?.enum
                return (
                  <div key={key}>
                    <label
                      htmlFor={`flow-${key}`}
                      className="block text-sm font-medium text-foreground mb-1"
                    >
                      {label}
                    </label>
                    {enumOptions && enumOptions.length > 0 ? (
                      <SingleSelectCombobox
                        value={placeholderValues[key] ?? ''}
                        onValueChange={(v) =>
                          setPlaceholderValues((prev) => ({ ...prev, [key]: v }))
                        }
                        options={enumOptions.map((v) => ({ value: v, label: v }))}
                        placeholder={`Select ${label.toLowerCase()}`}
                        className="w-full"
                      />
                    ) : (
                      <Input
                        id={`flow-${key}`}
                        value={placeholderValues[key] ?? ''}
                        onChange={(e) =>
                          setPlaceholderValues((prev) => ({
                            ...prev,
                            [key]: e.target.value,
                          }))
                        }
                        placeholder={
                          key === 'year'
                            ? 'e.g. 2026'
                            : key === 'month'
                              ? 'e.g. 03'
                              : key === 'day'
                                ? 'e.g. 15'
                                : key === 'client_name'
                                  ? 'e.g. Acme-Corp'
                                  : 'e.g. Renewal or Acme'
                        }
                        className="w-full"
                      />
                    )}
                  </div>
                )
              })}
              {resolvedName && (
                <p className="text-xs text-muted-foreground">
                  Flow name: <span className="font-mono text-foreground">{resolvedName}</span>
                </p>
              )}
            </>
          ) : (
            <div>
              <label
                htmlFor="flow-name"
                className="block text-sm font-medium text-foreground mb-1"
              >
                Name
              </label>
              <Input
                id="flow-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. 2026-03-Acme-Corp or My Flow"
                className="w-full"
                required={!useTemplateFields}
              />
              {templateForWorkflow && placeholderKeys.length === 0 && (
                <p className="mt-1 text-xs text-muted-foreground">
                  Template: {templateForWorkflow.template_string}
                </p>
              )}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-foreground mb-1">
              Workflow
            </label>
            <SingleSelectCombobox
              value={workflowId}
              onValueChange={setWorkflowId}
              options={workflowOptions}
              placeholder="Select workflow (optional)"
              clearable
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-1">
              Subject (optional)
            </label>
            <SubjectSelector
              value={subjectId}
              onChange={setSubjectId}
              placeholder="Link a subject to this flow"
            />
          </div>

          {submitError && (
            <div className="rounded-none border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {submitError}
            </div>
          )}

          <div className="flex items-center gap-2 pt-2">
            <Button type="submit" disabled={submitting}>
              {submitting ? (
                <>
                  <LoadingIcon />
                  Creating...
                </>
              ) : (
                'Create flow'
              )}
            </Button>
            <Link to="/flows">
              <Button type="button" variant="outline">
                <ArrowLeft className="w-4 h-4" />
                Cancel
              </Button>
            </Link>
          </div>
        </form>
      </div>
    </>
  )
}
