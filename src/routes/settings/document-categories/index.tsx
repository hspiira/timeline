import { createFileRoute } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { timelineApi } from '@/lib/api-client'
import { Plus, Pencil, Trash2, CheckCircle } from 'lucide-react'
import { DataTable } from '@/components/ui/DataTable'
import { Button } from '@/components/ui/button'
import { Modal } from '@/components/ui/Modal'
import { FormField, FormInput, FormTextarea } from '@/components/ui/FormField'
import { FormModalActions } from '@/components/ui/FormModalActions'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import { ErrorModal } from '@/components/ui/ErrorModal'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/settings/document-categories/')({
  component: DocumentCategoriesPage,
})

type DocumentCategoryListItem = components['schemas']['DocumentCategoryListItem']
type DocumentCategoryResponse = components['schemas']['DocumentCategoryResponse']
type DocumentCategoryCreateRequest =
  components['schemas']['DocumentCategoryCreateRequest']
type DocumentCategoryUpdateRequest =
  components['schemas']['DocumentCategoryUpdateRequest']

function DocumentCategoriesPage() {
  const authState = useRequireAuth()
  const [items, setItems] = useState<DocumentCategoryListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<DocumentCategoryResponse | null>(null)
  const [deleting, setDeleting] = useState<DocumentCategoryListItem | null>(
    null
  )
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const [category_name, setCategoryName] = useState('')
  const [display_name, setDisplayName] = useState('')
  const [description, setDescription] = useState('')
  const [metadataSchemaJson, setMetadataSchemaJson] = useState('')
  const [default_retention_days, setDefaultRetentionDays] = useState<string>('')
  const [is_active, setIsActive] = useState(true)

  useEffect(() => {
    if (authState.user) fetchList()
  }, [authState.user])

  const fetchList = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data, error: apiError } =
        await timelineApi.documentCategories.list({
          skip: 0,
          limit: 500,
        })
      if (apiError) {
        setError('Failed to load document categories')
        return
      }
      setItems(Array.isArray(data) ? data : [])
    } catch {
      setError('Failed to load document categories')
    } finally {
      setLoading(false)
    }
  }

  const openCreate = () => {
    setEditing(null)
    setCategoryName('')
    setDisplayName('')
    setDescription('')
    setMetadataSchemaJson('')
    setDefaultRetentionDays('')
    setIsActive(true)
    setFormError(null)
    setShowModal(true)
  }

  const openEdit = async (row: DocumentCategoryListItem) => {
    setFormError(null)
    try {
      const { data } = await timelineApi.documentCategories.get(row.id)
      if (data) {
        setEditing(data)
        setCategoryName(data.category_name)
        setDisplayName(data.display_name ?? '')
        setDescription(data.description ?? '')
        setMetadataSchemaJson(
          data.metadata_schema != null
            ? JSON.stringify(data.metadata_schema, null, 2)
            : ''
        )
        setDefaultRetentionDays(
          data.default_retention_days != null
            ? String(data.default_retention_days)
            : ''
        )
        setIsActive(data.is_active)
        setShowModal(true)
      }
    } catch {
      setError('Failed to load document category')
    }
  }

  const closeModal = () => {
    setShowModal(false)
    setEditing(null)
    setFormError(null)
  }

  const parseMetadataSchema = (): Record<string, unknown> | null => {
    if (!metadataSchemaJson.trim()) return null
    try {
      const v = JSON.parse(metadataSchemaJson)
      return typeof v === 'object' && v !== null ? v : null
    } catch {
      return undefined as unknown as null
    }
  }

  const handleSubmit = async () => {
    setFormError(null)
    const metadata_schema = parseMetadataSchema()
    if (metadataSchemaJson.trim() && metadata_schema === undefined) {
      setFormError('Invalid JSON for metadata schema')
      return
    }

    const retentionNum: number | null =
      default_retention_days.trim() === ''
        ? null
        : parseInt(default_retention_days, 10)
    if (
      default_retention_days.trim() !== '' &&
      (retentionNum === null || Number.isNaN(retentionNum) || retentionNum < 1)
    ) {
      setFormError('Retention days must be a positive number')
      return
    }

    setSaving(true)
    try {
      if (editing) {
        const body: DocumentCategoryUpdateRequest = {
          display_name: display_name || null,
          description: description || null,
          metadata_schema: metadata_schema ?? null,
          default_retention_days: retentionNum,
          is_active: is_active,
        }
        const { data, error: apiError } =
          await timelineApi.documentCategories.update(editing.id, body)
        if (apiError) {
          const msg =
            typeof apiError === 'object' && 'detail' in apiError
              ? String((apiError as { detail?: unknown }).detail)
              : 'Failed to update'
          setFormError(msg)
          return
        }
        if (data) {
          setItems((prev) =>
            prev.map((c) => (c.id === data.id ? { ...c, ...data } : c))
          )
          closeModal()
        }
      } else {
        const body: DocumentCategoryCreateRequest = {
          category_name: category_name.trim(),
          display_name: display_name.trim(),
          description: description.trim() || null,
          metadata_schema: metadata_schema ?? null,
          default_retention_days: retentionNum,
          is_active,
        }
        const { data, error: apiError } =
          await timelineApi.documentCategories.create(body)
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
              category_name: data.category_name,
              display_name: data.display_name,
              description: data.description,
              default_retention_days: data.default_retention_days,
              is_active: data.is_active,
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
      const { error: apiError } =
        await timelineApi.documentCategories.delete(deleting.id)
      if (apiError) throw new Error('Failed to delete')
      setItems((prev) => prev.filter((c) => c.id !== deleting.id))
      setDeleting(null)
    } catch {
      setError('Failed to delete document category')
      throw new Error('Failed to delete')
    }
  }

  if (!authState.user) return null

  const columns: ColumnDef<DocumentCategoryListItem>[] = [
    {
      accessorKey: 'category_name',
      header: 'Category',
      cell: ({ row }) => (
        <span className="font-medium text-foreground">
          {row.original.category_name}
        </span>
      ),
    },
    {
      accessorKey: 'display_name',
      header: 'Display Name',
      cell: ({ row }) => (
        <span className="text-muted-foreground">
          {row.original.display_name || '—'}
        </span>
      ),
    },
    {
      accessorKey: 'default_retention_days',
      header: 'Retention',
      cell: ({ row }) => (
        <span className="text-muted-foreground text-sm">
          {row.original.default_retention_days != null
            ? `${row.original.default_retention_days} days`
            : '—'}
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
          <Button
            variant="ghost"
            size="sm"
            title="Edit"
            onClick={() => openEdit(row.original)}
          >
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
          title={
            editing ? 'Edit Document Category' : 'Create Document Category'
          }
          maxWidth="max-w-lg"
          footer={
            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleSubmit()
              }}
            >
              {formError && (
                <p className="text-sm text-destructive mb-2">{formError}</p>
              )}
              <FormModalActions
                onCancel={closeModal}
                submitLabel={editing ? 'Save' : 'Create'}
                loadingLabel={editing ? 'Saving...' : 'Creating...'}
                loading={saving}
              />
            </form>
          }
        >
          <div className="space-y-4">
            <FormField label="Category name" required>
              <FormInput
                value={category_name}
                onChange={(e) => setCategoryName(e.target.value)}
                placeholder="e.g. contract"
                disabled={!!editing}
              />
            </FormField>
            <FormField label="Display name" required>
              <FormInput
                value={display_name}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="e.g. Contract"
              />
            </FormField>
            <FormField label="Description">
              <FormInput
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional"
              />
            </FormField>
            <FormField
              label="Metadata schema (JSON)"
              hint="Optional JSON Schema for document metadata"
            >
              <FormTextarea
                value={metadataSchemaJson}
                onChange={(e) => setMetadataSchemaJson(e.target.value)}
                placeholder='{"type":"object","properties":{}}'
                rows={4}
                className="font-mono text-sm"
              />
            </FormField>
            <FormField
              label="Default retention (days)"
              hint="Optional; positive integer"
            >
              <FormInput
                type="number"
                min={1}
                value={default_retention_days}
                onChange={(e) => setDefaultRetentionDays(e.target.value)}
                placeholder="e.g. 365"
              />
            </FormField>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={is_active}
                onChange={(e) => setIsActive(e.target.checked)}
                className="rounded border-input"
              />
              <span className="text-sm">Active</span>
            </label>
          </div>
        </Modal>
      )}

      {deleting && (
        <ConfirmModal
          isOpen={true}
          onClose={() => setDeleting(null)}
          title="Delete Document Category?"
          message="This action cannot be undone."
          confirmText="Delete"
          cancelText="Cancel"
          isDestructive={true}
          details={{
            Category: deleting.category_name,
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
          <h1 className="text-lg font-bold text-foreground">
            Document Categories
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Configure document categories, metadata schemas, and retention
          </p>
        </div>
        <Button variant="primary" size="md" onClick={openCreate}>
          <Plus className="w-4 h-4" />
          Category
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
          title: 'No document categories yet',
          description:
            'Create a category to use when uploading documents',
          action: (
            <Button onClick={openCreate} variant="primary" size="md">
              <Plus className="w-4 h-4" />
              Category
            </Button>
          ),
        }}
      />
    </>
  )
}
