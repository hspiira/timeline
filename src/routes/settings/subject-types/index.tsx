import { createFileRoute } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { CheckCircle, Pencil, Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { AttributeSchemaBuilder } from '@/components/ui/AttributeSchemaBuilder'
import { Button } from '@/components/ui/button'
import { ColorSwatchPicker } from '@/components/ui/ColorSwatchPicker'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import { DataTable } from '@/components/ui/DataTable'
import { ErrorModal } from '@/components/ui/ErrorModal'
import { FormField, FormInput } from '@/components/ui/FormField'
import { FormModalActions } from '@/components/ui/FormModalActions'
import { IconPicker } from '@/components/ui/IconPicker'
import { Modal } from '@/components/ui/Modal'
import { Textarea } from '@/components/ui/textarea'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { timelineApi } from '@/lib/api-client'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/settings/subject-types/')({
  component: SubjectTypesPage,
})

type SubjectTypeListItem = components['schemas']['SubjectTypeListItem']
type SubjectTypeResponse = components['schemas']['SubjectTypeResponse']
type SubjectTypeCreateRequest = components['schemas']['SubjectTypeCreateRequest']
type SubjectTypeUpdateRequest = components['schemas']['SubjectTypeUpdateRequest']

function SubjectTypesPage() {
  const authState = useRequireAuth()
  const [items, setItems] = useState<SubjectTypeListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<SubjectTypeResponse | null>(null)
  const [deleting, setDeleting] = useState<SubjectTypeListItem | null>(null)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const [type_name, setTypeName] = useState('')
  const [display_name, setDisplayName] = useState('')
  const [description, setDescription] = useState('')
  const [schemaJson, setSchemaJson] = useState('')
  const [is_active, setIsActive] = useState(true)
  const [icon, setIcon] = useState('')
  const [color, setColor] = useState('')
  const [has_timeline, setHasTimeline] = useState(true)
  const [allow_documents, setAllowDocuments] = useState(true)

  useEffect(() => {
    if (authState.user) fetchList()
  }, [authState.user])

  const fetchList = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data, error: apiError } = await timelineApi.subjectTypes.list({
        skip: 0,
        limit: 500,
      })
      if (apiError) {
        setError('Failed to load subject types')
        return
      }
      setItems(Array.isArray(data) ? data : [])
    } catch {
      setError('Failed to load subject types')
    } finally {
      setLoading(false)
    }
  }

  const openCreate = () => {
    setEditing(null)
    setTypeName('')
    setDisplayName('')
    setDescription('')
    setSchemaJson('')
    setIsActive(true)
    setIcon('')
    setColor('')
    setHasTimeline(true)
    setAllowDocuments(true)
    setFormError(null)
    setShowModal(true)
  }

  const openEdit = async (row: SubjectTypeListItem) => {
    setFormError(null)
    try {
      const { data } = await timelineApi.subjectTypes.get(row.id)
      if (data) {
        setEditing(data)
        setTypeName(data.type_name)
        setDisplayName(data.display_name ?? '')
        setDescription(data.description ?? '')
        setSchemaJson(data.schema != null ? JSON.stringify(data.schema, null, 2) : '')
        setIsActive(data.is_active)
        setIcon(data.icon ?? '')
        setColor(data.color ?? '')
        setHasTimeline(data.has_timeline)
        setAllowDocuments(data.allow_documents)
        setShowModal(true)
      }
    } catch {
      setError('Failed to load subject type')
    }
  }

  const closeModal = () => {
    setShowModal(false)
    setEditing(null)
    setFormError(null)
  }

  const parseSchema = (): Record<string, unknown> | null => {
    if (!schemaJson.trim()) return null
    try {
      const v = JSON.parse(schemaJson)
      return typeof v === 'object' && v !== null ? v : null
    } catch {
      return undefined as unknown as null
    }
  }

  const handleSubmit = async () => {
    setFormError(null)
    const schema = parseSchema()
    if (schemaJson.trim() && schema === undefined) {
      setFormError('Invalid JSON for schema')
      return
    }

    setSaving(true)
    try {
      if (editing) {
        const body: SubjectTypeUpdateRequest = {
          display_name: display_name || null,
          description: description || null,
          schema: schema ?? null,
          is_active: is_active,
          icon: icon || null,
          color: color || null,
          has_timeline: has_timeline,
          allow_documents: allow_documents,
        }
        const { data, error: apiError } = await timelineApi.subjectTypes.update(editing.id, body)
        if (apiError) {
          const msg =
            typeof apiError === 'object' && 'detail' in apiError
              ? String((apiError as { detail?: unknown }).detail)
              : 'Failed to update'
          setFormError(msg)
          return
        }
        if (data) {
          setItems((prev) => prev.map((s) => (s.id === data.id ? { ...s, ...data } : s)))
          closeModal()
        }
      } else {
        const body: SubjectTypeCreateRequest = {
          type_name: type_name.trim(),
          display_name: display_name.trim(),
          description: description.trim() || null,
          schema: schema ?? null,
          is_active,
          icon: icon.trim() || null,
          color: color.trim() || null,
          has_timeline,
          allow_documents,
        }
        const { data, error: apiError } = await timelineApi.subjectTypes.create(body)
        if (apiError) {
          const msg =
            typeof apiError === 'object' && 'detail' in apiError
              ? String((apiError as { detail?: unknown }).detail)
              : 'Failed to create'
          setFormError(msg)
          return
        }
        if (data) {
          setItems((prev) => [
            {
              id: data.id,
              tenant_id: data.tenant_id,
              type_name: data.type_name,
              display_name: data.display_name,
              description: data.description,
              version: data.version,
              is_active: data.is_active,
              icon: data.icon,
              color: data.color,
              has_timeline: data.has_timeline,
              allow_documents: data.allow_documents,
            },
            ...prev,
          ])
          closeModal()
        }
      }
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteConfirm = async () => {
    if (!deleting) return
    try {
      const { error: apiError } = await timelineApi.subjectTypes.delete(deleting.id)
      if (apiError) throw new Error('Failed to delete')
      setItems((prev) => prev.filter((s) => s.id !== deleting.id))
      setDeleting(null)
    } catch {
      setError('Failed to delete subject type')
      throw new Error('Failed to delete')
    }
  }

  if (!authState.user) return null

  const columns: ColumnDef<SubjectTypeListItem>[] = [
    {
      accessorKey: 'type_name',
      header: 'Type',
      cell: ({ row }) => (
        <span className="font-medium text-foreground">{row.original.type_name}</span>
      ),
    },
    {
      accessorKey: 'display_name',
      header: 'Display Name',
      cell: ({ row }) => (
        <span className="text-muted-foreground">{row.original.display_name || '—'}</span>
      ),
    },
    {
      accessorKey: 'version',
      header: 'Version',
      cell: ({ row }) => (
        <span className="text-muted-foreground text-sm">v{row.original.version}</span>
      ),
    },
    {
      id: 'flags',
      header: 'Flags',
      cell: ({ row }) => (
        <span className="text-xs text-muted-foreground">
          {row.original.has_timeline ? 'Timeline' : ''}
          {row.original.has_timeline && row.original.allow_documents ? ' · ' : ''}
          {row.original.allow_documents ? 'Documents' : ''}
        </span>
      ),
    },
    {
      id: 'status',
      header: 'Status',
      cell: ({ row }) =>
        row.original.is_active ? (
          <div className="flex items-center gap-1 text-green-600 dark:text-green-400">
            <CheckCircle className="w-3 h-3" />
            <span className="text-xs">Active</span>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">Inactive</span>
        ),
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => (
        <div className="flex items-center justify-end gap-1">
          <Button variant="ghost" size="sm" title="Edit" onClick={() => openEdit(row.original)}>
            <Pencil className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            title="Delete"
            onClick={() => setDeleting(row.original)}
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      ),
    },
  ]

  return (
    <>
      {showModal && (
        <Modal
          isOpen={true}
          onClose={closeModal}
          title={editing ? 'Edit Subject Type' : 'Create Subject Type'}
          maxWidth="max-w-4xl"
          footer={
            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleSubmit()
              }}
            >
              {formError && <p className="text-sm text-destructive mb-2">{formError}</p>}
              <FormModalActions
                onCancel={closeModal}
                submitLabel={editing ? 'Save' : 'Create'}
                loadingLabel={editing ? 'Saving...' : 'Creating...'}
                loading={saving}
              />
            </form>
          }
        >
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <FormField label="Type name" required>
                <FormInput
                  value={type_name}
                  onChange={(e) => setTypeName(e.target.value)}
                  placeholder="e.g. client"
                  disabled={!!editing}
                />
              </FormField>
              <FormField label="Display name" required>
                <FormInput
                  value={display_name}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="e.g. Client"
                />
              </FormField>
            </div>
            <FormField label="Description">
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional"
                rows={3}
                className="min-h-[80px] resize-y text-sm"
              />
            </FormField>
            <FormField
              label="Attribute schema"
              hint="Optional: define custom fields for subjects of this type. Use “Add fields” or edit JSON."
            >
              <AttributeSchemaBuilder
                value={schemaJson}
                onChange={setSchemaJson}
                placeholder='{"type":"object","properties":{}}'
              />
            </FormField>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full min-w-0 m-0 justify-items-stretch">
              <div className="min-w-0">
                <FormField label="Icon" hint="Shown in subject list and cards">
                  <IconPicker value={icon} onChange={setIcon} allowClear={true} />
                </FormField>
              </div>
              <div className="min-w-0">
                <FormField label="Color" hint="Theme for this type">
                  <ColorSwatchPicker value={color} onChange={setColor} allowClear={true} />
                </FormField>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={is_active}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="rounded border-input"
                />
                <span className="text-sm">Active</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={has_timeline}
                  onChange={(e) => setHasTimeline(e.target.checked)}
                  className="rounded border-input"
                />
                <span className="text-sm">Has timeline</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={allow_documents}
                  onChange={(e) => setAllowDocuments(e.target.checked)}
                  className="rounded border-input"
                />
                <span className="text-sm">Allow documents</span>
              </label>
            </div>
          </div>
        </Modal>
      )}

      {deleting && (
        <ConfirmModal
          isOpen={true}
          onClose={() => setDeleting(null)}
          title="Delete Subject Type?"
          message="This action cannot be undone."
          confirmText="Delete"
          cancelText="Cancel"
          isDestructive={true}
          details={{
            Type: deleting.type_name,
            'Display name': deleting.display_name || '—',
          }}
          onConfirm={handleDeleteConfirm}
        />
      )}

      <ErrorModal
        open={!!error}
        onClose={() => setError(null)}
        title="Error"
        message={error ?? ''}
      />

      <div className="flex items-center justify-between mb-3">
        <div>
          <h1 className="text-lg font-bold text-foreground">Subject Types</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Configure subject types, display names, and optional attribute schemas
          </p>
        </div>
        <Button variant="primary" size="md" onClick={openCreate}>
          <Plus className="w-4 h-4" />
          Subject Type
        </Button>
      </div>

      <DataTable
        data={items}
        columns={columns}
        isLoading={loading}
        isEmpty={items.length === 0}
        compact={true}
        enablePagination={true}
        pageSize={10}
        emptyState={{
          title: 'No subject types yet',
          description: 'Create a subject type to use in the subject list',
          action: (
            <Button onClick={openCreate} variant="primary" size="md">
              <Plus className="w-4 h-4" />
              Subject Type
            </Button>
          ),
        }}
      />
    </>
  )
}
