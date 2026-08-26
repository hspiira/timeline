import { createFileRoute } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { Pencil, Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import { DataTable } from '@/components/ui/DataTable'
import { ErrorModal } from '@/components/ui/ErrorModal'
import { FormError, FormField, FormInput, FormTextarea } from '@/components/ui/FormField'
import { FormModalActions } from '@/components/ui/FormModalActions'
import { Modal } from '@/components/ui/Modal'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { timelineApi } from '@/lib/api-client'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/settings/relationship-kinds/')({
  component: RelationshipKindsPage,
})

type RelationshipKindListItem = components['schemas']['RelationshipKindListItem']
type RelationshipKindResponse = components['schemas']['RelationshipKindResponse']

function RelationshipKindsPage() {
  const authState = useRequireAuth()
  const [items, setItems] = useState<RelationshipKindListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<RelationshipKindResponse | null>(null)
  const [deleting, setDeleting] = useState<RelationshipKindListItem | null>(null)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const [kind, setKind] = useState('')
  const [display_name, setDisplayName] = useState('')
  const [description, setDescription] = useState('')
  const [payloadSchemaJson, setPayloadSchemaJson] = useState('')

  useEffect(() => {
    if (authState.user) fetchList()
  }, [authState.user])

  const fetchList = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data, error: apiError } = await timelineApi.relationshipKinds.list()
      if (apiError) {
        setError('Failed to load relationship kinds')
        return
      }
      setItems(Array.isArray(data) ? data : [])
    } catch {
      setError('Failed to load relationship kinds')
    } finally {
      setLoading(false)
    }
  }

  const openCreate = () => {
    setEditing(null)
    setKind('')
    setDisplayName('')
    setDescription('')
    setPayloadSchemaJson('')
    setFormError(null)
    setShowModal(true)
  }

  const openEdit = async (row: RelationshipKindListItem) => {
    setFormError(null)
    try {
      const { data } = await timelineApi.relationshipKinds.get(row.id)
      if (data) {
        setEditing(data)
        setKind(data.kind)
        setDisplayName(data.display_name ?? '')
        setDescription(data.description ?? '')
        setPayloadSchemaJson(
          data.payload_schema != null ? JSON.stringify(data.payload_schema, null, 2) : '',
        )
        setShowModal(true)
      }
    } catch {
      setError('Failed to load relationship kind')
    }
  }

  const closeModal = () => {
    setShowModal(false)
    setEditing(null)
    setFormError(null)
  }

  const parsePayloadSchema = (): Record<string, unknown> | null => {
    if (!payloadSchemaJson.trim()) return null
    try {
      return JSON.parse(payloadSchemaJson) as Record<string, unknown>
    } catch {
      return undefined
    }
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    const payloadSchema = parsePayloadSchema()
    if (payloadSchema === undefined) {
      setFormError('Payload schema must be valid JSON')
      return
    }
    setSaving(true)
    try {
      if (editing) {
        const { error: apiError } = await timelineApi.relationshipKinds.update(editing.id, {
          display_name: display_name.trim() || null,
          description: description.trim() || null,
          payload_schema: payloadSchema,
        })
        if (apiError) {
          setFormError(
            typeof apiError === 'object' && 'detail' in apiError
              ? String((apiError as { detail: unknown }).detail)
              : 'Failed to update',
          )
          return
        }
      } else {
        if (!kind.trim()) {
          setFormError('Kind is required')
          return
        }
        if (!display_name.trim()) {
          setFormError('Display name is required')
          return
        }
        const { error: apiError } = await timelineApi.relationshipKinds.create({
          kind: kind.trim(),
          display_name: display_name.trim(),
          description: description.trim() || null,
          payload_schema: payloadSchema,
        })
        if (apiError) {
          setFormError(
            typeof apiError === 'object' && 'detail' in apiError
              ? String((apiError as { detail: unknown }).detail)
              : 'Failed to create',
          )
          return
        }
      }
      closeModal()
      fetchList()
    } finally {
      setSaving(false)
    }
  }

  const handleConfirmDelete = async () => {
    if (!deleting) return
    try {
      const { error: apiError } = await timelineApi.relationshipKinds.delete(deleting.id)
      if (apiError) {
        setError(
          typeof apiError === 'object' && 'detail' in apiError
            ? String((apiError as { detail: unknown }).detail)
            : 'Failed to delete',
        )
        return
      }
      setDeleting(null)
      fetchList()
    } catch {
      setError('Failed to delete')
    }
  }

  if (!authState.user) return null

  const columns: ColumnDef<RelationshipKindListItem>[] = [
    {
      accessorKey: 'kind',
      header: 'Kind',
      cell: ({ row }) => (
        <span className="font-mono text-sm text-foreground">{row.original.kind}</span>
      ),
    },
    {
      accessorKey: 'display_name',
      header: 'Display name',
      cell: ({ row }) => (
        <span className="text-sm text-foreground">{row.original.display_name}</span>
      ),
    },
    {
      accessorKey: 'description',
      header: 'Description',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground truncate max-w-[200px] block">
          {row.original.description ?? '—'}
        </span>
      ),
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={() => openEdit(row.original)} title="Edit">
            <Pencil className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setDeleting(row.original)}
            title="Delete"
            className="text-destructive hover:text-destructive"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      ),
    },
  ]

  return (
    <>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-foreground">Relationship kinds</h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Define allowed relationship types (e.g. client_of, parent_of) used when linking
              subjects.
            </p>
          </div>
          <Button variant="primary" size="md" onClick={openCreate}>
            <Plus className="w-4 h-4" />
            Add kind
          </Button>
        </div>

        {error && (
          <div className="rounded-none border border-destructive/50 bg-destructive/10 px-4 py-2 text-sm text-destructive">
            {error}
          </div>
        )}

        <DataTable
          data={items}
          columns={columns}
          isLoading={loading}
          isEmpty={items.length === 0}
          compact
          enablePagination={false}
          emptyState={{
            title: 'No relationship kinds',
            description:
              'Add kinds to restrict which relationship types can be used when linking subjects. If none are defined, any kind is allowed.',
            action: (
              <Button onClick={openCreate} variant="primary" size="md">
                <Plus className="w-4 h-4" />
                Add kind
              </Button>
            ),
          }}
        />
      </div>

      {/* Create/Edit modal */}
      <Modal
        isOpen={showModal}
        onClose={closeModal}
        title={editing ? 'Edit relationship kind' : 'Add relationship kind'}
        maxWidth="max-w-md"
      >
        <form onSubmit={handleSave} className="space-y-4">
          {formError && <FormError message={formError} />}
          <FormField
            label="Kind"
            required
            hint="e.g. client_of, parent_of (alphanumeric + underscore)"
          >
            <FormInput
              value={kind}
              onChange={(e) => setKind(e.target.value)}
              placeholder="client_of"
              disabled={!!editing}
            />
          </FormField>
          <FormField label="Display name" required>
            <FormInput
              value={display_name}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Client of"
            />
          </FormField>
          <FormField label="Description (optional)">
            <FormInput
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Subject is a client of the target"
            />
          </FormField>
          <FormField
            label="Payload schema (optional)"
            hint="JSON object for validating relationship payload"
          >
            <FormTextarea
              value={payloadSchemaJson}
              onChange={(e) => setPayloadSchemaJson(e.target.value)}
              placeholder='{"type": "object", "properties": {}}'
              rows={4}
              className="font-mono text-xs"
            />
          </FormField>
          <FormModalActions
            onCancel={closeModal}
            loading={saving}
            submitLabel={editing ? 'Save' : 'Create'}
          />
        </form>
      </Modal>

      <ConfirmModal
        isOpen={!!deleting}
        onClose={() => setDeleting(null)}
        title="Delete relationship kind?"
        message="This may prevent adding new relationships that use this kind. Existing relationships are not removed."
        confirmText="Delete"
        cancelText="Cancel"
        isDestructive
        details={
          deleting ? { kind: deleting.kind, 'display name': deleting.display_name } : undefined
        }
        onConfirm={handleConfirmDelete}
      />

      <ErrorModal
        open={!!error}
        onClose={() => setError(null)}
        title="Error"
        message={error ?? ''}
      />
    </>
  )
}
