import { useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Pencil, Plus, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import { SingleSelectCombobox } from '@/components/ui/combobox'
import { DataTable } from '@/components/ui/DataTable'
import { FormField, FormInput } from '@/components/ui/FormField'
import { FormModalActions } from '@/components/ui/FormModalActions'
import { LoadingIcon } from '@/components/ui/icons'
import { Modal } from '@/components/ui/Modal'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { timelineApi } from '@/lib/api-client'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/settings/naming-templates/')({
  component: NamingTemplatesPage,
})

type NamingTemplate = components['schemas']['NamingTemplateResponse']
type Workflow = components['schemas']['WorkflowResponse']
type SubjectTypeListItem = components['schemas']['SubjectTypeListItem']
type DocumentCategoryListItem = components['schemas']['DocumentCategoryListItem']

const SCOPE_TYPES = [
  { value: 'flow', label: 'Flow' },
  { value: 'subject', label: 'Subject type' },
  { value: 'document', label: 'Document category' },
]

/** Preset template patterns so users don't have to type format strings. */
const TEMPLATE_PRESETS = [
  { id: '', label: 'Custom (build your own)', template: '' },
  {
    id: 'year-month-name',
    label: 'Year-Month-Name (e.g. 2026-03-Acme)',
    template: '{year}-{month}-{name}',
  },
  {
    id: 'year-month-client',
    label: 'Year-Month-Client (e.g. 2026-03-Acme-Corp)',
    template: '{year}-{month}-{client_name}',
  },
  {
    id: 'year-name',
    label: 'Year-Name (e.g. 2026-Renewal)',
    template: '{year}-{name}',
  },
  {
    id: 'year-month-day',
    label: 'Year-Month-Day (e.g. 2026-03-15)',
    template: '{year}-{month}-{day}',
  },
]

/** Placeholders users can insert without typing. Backend allows only word chars inside braces. */
const PLACEHOLDER_INSERT = [
  { key: 'year', label: 'Year' },
  { key: 'month', label: 'Month' },
  { key: 'day', label: 'Day' },
  { key: 'name', label: 'Name' },
  { key: 'client_name', label: 'Client name' },
]

function exampleFromTemplate(template: string): string {
  const examples: Record<string, string> = {
    year: '2026',
    month: '03',
    day: '15',
    name: 'Acme',
    client_name: 'Acme-Corp',
  }
  return template.replace(/\{(\w+)\}/g, (_, key) => examples[key] ?? key)
}

function NamingTemplatesPage() {
  const authState = useRequireAuth()
  const [items, setItems] = useState<NamingTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<NamingTemplate | null>(null)
  const [deleting, setDeleting] = useState<NamingTemplate | null>(null)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const [scope_type, setScopeType] = useState('flow')
  const [scope_id, setScopeId] = useState('')
  const [template_string, setTemplateString] = useState('')
  const [templatePreset, setTemplatePreset] = useState('')

  const { data: workflows = [] } = useQuery({
    queryKey: ['workflows'],
    queryFn: async () => {
      const { data, error } = await timelineApi.workflows.list({ limit: 500 })
      return error ? [] : Array.isArray(data) ? data : []
    },
    enabled: !!authState.user,
  })

  const { data: subjectTypes = [] } = useQuery({
    queryKey: ['subject-types'],
    queryFn: async () => {
      const { data, error } = await timelineApi.subjectTypes.list({
        skip: 0,
        limit: 500,
      })
      return error ? [] : Array.isArray(data) ? data : []
    },
    enabled: !!authState.user,
  })

  const { data: documentCategories = [] } = useQuery({
    queryKey: ['document-categories'],
    queryFn: async () => {
      const { data, error } = await timelineApi.documentCategories.list({
        skip: 0,
        limit: 500,
      })
      return error ? [] : Array.isArray(data) ? data : []
    },
    enabled: !!authState.user,
  })

  const scopeOptions = useMemo(() => {
    if (scope_type === 'flow') {
      return workflows.map((w: Workflow) => ({
        value: w.id,
        label: w.name || w.id,
      }))
    }
    if (scope_type === 'subject') {
      return subjectTypes.map((s: SubjectTypeListItem) => ({
        value: s.id,
        label: s.display_name || s.type_name || s.id,
      }))
    }
    if (scope_type === 'document') {
      return documentCategories.map((c: DocumentCategoryListItem) => ({
        value: c.id,
        label: c.display_name || c.category_name || c.id,
      }))
    }
    return []
  }, [scope_type, workflows, subjectTypes, documentCategories])

  const scopeLabel = (t: NamingTemplate) => {
    if (t.scope_type === 'flow') {
      const w = workflows.find((x: Workflow) => x.id === t.scope_id)
      return w?.name ?? t.scope_id
    }
    if (t.scope_type === 'subject') {
      const s = subjectTypes.find((x: SubjectTypeListItem) => x.id === t.scope_id)
      return (s?.display_name || s?.type_name) ?? t.scope_id
    }
    if (t.scope_type === 'document') {
      const c = documentCategories.find((x: DocumentCategoryListItem) => x.id === t.scope_id)
      return (c?.display_name || c?.category_name) ?? t.scope_id
    }
    return t.scope_id
  }

  const fetchList = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data, error: apiError } = await timelineApi.namingTemplates.list({
        skip: 0,
        limit: 500,
      })
      if (apiError) {
        setError('Failed to load naming templates')
        return
      }
      setItems(Array.isArray(data) ? data : [])
    } catch {
      setError('Failed to load naming templates')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (authState.user) fetchList()
  }, [authState.user, fetchList])

  const openCreate = () => {
    setEditing(null)
    setScopeType('flow')
    setScopeId('')
    setTemplateString('')
    setTemplatePreset('')
    setFormError(null)
    setShowModal(true)
  }

  const handleScopeTypeChange = (newType: string) => {
    setScopeType(newType)
    setScopeId('')
  }

  const matchPreset = (t: string) => TEMPLATE_PRESETS.find((p) => p.template === t)?.id ?? ''

  const openEdit = (row: NamingTemplate) => {
    setEditing(row)
    setScopeType(row.scope_type)
    setScopeId(row.scope_id)
    setTemplateString(row.template_string)
    setTemplatePreset(matchPreset(row.template_string))
    setFormError(null)
    setShowModal(true)
  }

  const closeModal = () => {
    setShowModal(false)
    setEditing(null)
    setFormError(null)
  }

  const handleSave = async () => {
    if (!template_string.trim()) {
      setFormError('Template string is required')
      return
    }
    if (!scope_id.trim()) {
      setFormError('Scope ID is required (e.g. workflow id for flow scope)')
      return
    }
    setSaving(true)
    setFormError(null)
    try {
      if (editing) {
        const { error: apiError } = await timelineApi.namingTemplates.update(editing.id, {
          template_string: template_string.trim(),
        })
        if (apiError) {
          setFormError('Failed to update template')
          setSaving(false)
          return
        }
      } else {
        const { error: apiError } = await timelineApi.namingTemplates.create({
          scope_type: scope_type as 'flow' | 'subject' | 'document',
          scope_id: scope_id.trim(),
          template_string: template_string.trim(),
        })
        if (apiError) {
          setFormError((apiError as { detail?: string }).detail ?? 'Failed to create template')
          setSaving(false)
          return
        }
      }
      closeModal()
      fetchList()
    } catch {
      setFormError('An unexpected error occurred')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!deleting) return
    try {
      const { error: apiError } = await timelineApi.namingTemplates.delete(deleting.id)
      if (apiError) {
        setError('Failed to delete template')
        setDeleting(null)
        return
      }
      setDeleting(null)
      fetchList()
    } catch {
      setError('Failed to delete template')
      setDeleting(null)
    }
  }

  const columns: Array<ColumnDef<NamingTemplate>> = [
    {
      accessorKey: 'scope_type',
      header: 'Scope type',
      cell: ({ row }) => row.original.scope_type,
    },
    {
      accessorKey: 'scope_id',
      header: 'Scope',
      cell: ({ row }) => <span className="text-sm">{scopeLabel(row.original)}</span>,
    },
    {
      accessorKey: 'template_string',
      header: 'Template',
      cell: ({ row }) => <span className="font-mono text-sm">{row.original.template_string}</span>,
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => {
        const t = row.original
        return (
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="sm" onClick={() => openEdit(t)} title="Edit">
              <Pencil className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive hover:text-destructive"
              onClick={() => setDeleting(t)}
              title="Delete"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        )
      },
    },
  ]

  if (!authState.user) return null

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold text-foreground">Naming templates</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Define name patterns for flows, subjects, and documents (e.g.{' '}
            <code className="text-xs">{'{year}-{month}-{client_name}'}</code>)
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="w-4 h-4" />
          Add template
        </Button>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-muted-foreground py-8">
          <LoadingIcon />
          Loading...
        </div>
      )}
      {error && <p className="text-sm text-destructive py-2">{error}</p>}
      {!loading && !error && (
        <DataTable
          data={items}
          columns={columns}
          isLoading={false}
          isEmpty={items.length === 0}
          variant="default"
        />
      )}

      <Modal
        isOpen={showModal}
        onClose={closeModal}
        title={editing ? 'Edit naming template' : 'New naming template'}
        maxWidth="max-w-2xl"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSave()
          }}
          className="space-y-4"
        >
          <FormField label="Scope type">
            <SingleSelectCombobox
              value={scope_type}
              onValueChange={editing ? setScopeType : handleScopeTypeChange}
              options={SCOPE_TYPES}
              placeholder="Scope type"
              disabled={!!editing}
            />
          </FormField>
          <FormField
            label={
              scope_type === 'flow'
                ? 'Workflow'
                : scope_type === 'subject'
                  ? 'Subject type'
                  : 'Document category'
            }
          >
            <SingleSelectCombobox
              value={scope_id}
              onValueChange={setScopeId}
              options={[
                {
                  value: '',
                  label:
                    scope_type === 'flow'
                      ? 'Select workflow'
                      : scope_type === 'subject'
                        ? 'Select subject type'
                        : 'Select document category',
                },
                ...scopeOptions,
              ]}
              placeholder={
                scope_type === 'flow'
                  ? 'Select workflow'
                  : scope_type === 'subject'
                    ? 'Select subject type'
                    : 'Select document category'
              }
              clearable={!editing}
              disabled={!!editing}
              className="w-full"
            />
          </FormField>
          <FormField label="Name pattern">
            <SingleSelectCombobox
              value={templatePreset}
              onValueChange={(value) => {
                setTemplatePreset(value)
                const preset = TEMPLATE_PRESETS.find((p) => p.id === value)
                if (preset?.template) setTemplateString(preset.template)
              }}
              options={TEMPLATE_PRESETS.map((p) => ({
                value: p.id,
                label: p.label,
              }))}
              placeholder="Choose a pattern or build your own"
              clearable
              className="w-full mb-2"
            />
            <FormInput
              value={template_string}
              onChange={(e) => {
                setTemplateString(e.target.value)
                setTemplatePreset(matchPreset(e.target.value))
              }}
              placeholder="e.g. {year}-{month}-{name}"
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground mt-1.5 mb-2">
              Add placeholders with the buttons below so names follow a standard format. Only
              letters, numbers and underscores inside braces (e.g. {'{client_name}'}).
            </p>
            <div className="flex flex-wrap gap-1.5">
              {PLACEHOLDER_INSERT.map(({ key, label }) => (
                <Button
                  key={key}
                  type="button"
                  variant="outline"
                  size="sm"
                  className="text-xs font-mono"
                  onClick={() =>
                    setTemplateString((s) => `${s}${s && !s.endsWith('-') ? '-' : ''}{${key}}`)
                  }
                >
                  + {label}
                </Button>
              ))}
            </div>
            {template_string.trim() && (
              <p className="text-xs text-muted-foreground mt-2">
                Example:{' '}
                <span className="font-mono text-foreground">
                  {exampleFromTemplate(template_string)}
                </span>
              </p>
            )}
          </FormField>
          {formError && <p className="text-sm text-destructive">{formError}</p>}
          <FormModalActions
            onCancel={closeModal}
            submitLabel={editing ? 'Save' : 'Create'}
            loadingLabel={editing ? 'Saving...' : 'Creating...'}
            loading={saving}
          />
        </form>
      </Modal>

      {deleting && (
        <ConfirmModal
          isOpen={true}
          onClose={() => setDeleting(null)}
          onConfirm={handleDelete}
          title="Delete naming template"
          message={`Delete template "${deleting.template_string}" for ${deleting.scope_type} / ${scopeLabel(deleting)}?`}
          confirmText="Delete"
          isDestructive
        />
      )}
    </>
  )
}
