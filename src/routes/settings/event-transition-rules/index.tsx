import { createFileRoute } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { timelineApi } from '@/lib/api-client'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import { DataTable } from '@/components/ui/DataTable'
import { Button } from '@/components/ui/button'
import { Modal } from '@/components/ui/Modal'
import { FormField, FormInput, FormTextarea, FormError } from '@/components/ui/FormField'
import { FormModalActions } from '@/components/ui/FormModalActions'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import { ErrorModal } from '@/components/ui/ErrorModal'
import { getApiErrorMessage } from '@/lib/api-utils'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/settings/event-transition-rules/')({
  component: EventTransitionRulesPage,
})

type EventTransitionRuleResponse = components['schemas']['EventTransitionRuleResponse']
type EventTransitionRuleCreateRequest =
  components['schemas']['EventTransitionRuleCreateRequest']
type EventTransitionRuleUpdate =
  components['schemas']['EventTransitionRuleUpdate']

function parsePriorTypes(value: string): string[] {
  return value
    .split(/[\n,]+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

function EventTransitionRulesPage() {
  const authState = useRequireAuth()
  const [items, setItems] = useState<EventTransitionRuleResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<EventTransitionRuleResponse | null>(null)
  const [deleting, setDeleting] = useState<EventTransitionRuleResponse | null>(null)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const [event_type, setEventType] = useState('')
  const [requiredPriorInput, setRequiredPriorInput] = useState('')
  const [description, setDescription] = useState('')

  useEffect(() => {
    if (authState.user) fetchList()
  }, [authState.user])

  const fetchList = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data, error: apiError } =
        await timelineApi.eventTransitionRules.list({ skip: 0, limit: 500 })
      if (apiError) {
        setError('Failed to load event transition rules')
        return
      }
      setItems(Array.isArray(data) ? data : [])
    } catch {
      setError('Failed to load event transition rules')
    } finally {
      setLoading(false)
    }
  }

  const openCreate = () => {
    setEditing(null)
    setEventType('')
    setRequiredPriorInput('')
    setDescription('')
    setFormError(null)
    setShowModal(true)
  }

  const openEdit = (row: EventTransitionRuleResponse) => {
    setEditing(row)
    setEventType(row.event_type)
    setRequiredPriorInput(row.required_prior_event_types.join(', '))
    setDescription(row.description ?? '')
    setFormError(null)
    setShowModal(true)
  }

  const closeModal = () => {
    setShowModal(false)
    setEditing(null)
    setFormError(null)
  }

  const handleSubmit = async () => {
    setFormError(null)
    const required_prior_event_types = parsePriorTypes(requiredPriorInput)
    if (required_prior_event_types.length === 0) {
      setFormError('At least one required prior event type is needed')
      return
    }
    if (!event_type.trim()) {
      setFormError('Event type is required')
      return
    }

    setSaving(true)
    try {
      if (editing) {
        const body: EventTransitionRuleUpdate = {
          required_prior_event_types,
          description: description.trim() || null,
        }
        const { data, error: apiError } =
          await timelineApi.eventTransitionRules.update(editing.id, body)
        if (apiError) {
          setFormError(getApiErrorMessage(apiError, 'Failed to update'))
          return
        }
        if (data) {
          setItems((prev) =>
            prev.map((r) => (r.id === data.id ? data : r))
          )
          closeModal()
        }
      } else {
        const body: EventTransitionRuleCreateRequest = {
          event_type: event_type.trim(),
          required_prior_event_types,
          description: description.trim() || null,
        }
        const { data, error: apiError } =
          await timelineApi.eventTransitionRules.create(body)
        if (apiError) {
          setFormError(getApiErrorMessage(apiError, 'Failed to create'))
          return
        }
        if (data) {
          setItems((prev) => [data, ...prev])
          closeModal()
        }
      }
    } catch {
      setFormError('An unexpected error occurred')
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteConfirm = async () => {
    if (!deleting) return
    try {
      const { error: apiError } =
        await timelineApi.eventTransitionRules.delete(deleting.id)
      if (apiError) throw new Error('Failed to delete')
      setItems((prev) => prev.filter((r) => r.id !== deleting.id))
      setDeleting(null)
    } catch {
      setError('Failed to delete event transition rule')
      throw new Error('Failed to delete')
    }
  }

  if (!authState.user) return null

  const columns: ColumnDef<EventTransitionRuleResponse>[] = [
    {
      accessorKey: 'event_type',
      header: 'Event type',
      cell: ({ row }) => (
        <span className="font-medium text-foreground">
          {row.original.event_type}
        </span>
      ),
    },
    {
      accessorKey: 'required_prior_event_types',
      header: 'Required prior',
      cell: ({ row }) => (
        <span className="text-muted-foreground text-sm">
          {row.original.required_prior_event_types.join(', ') || '—'}
        </span>
      ),
    },
    {
      accessorKey: 'description',
      header: 'Description',
      cell: ({ row }) => (
        <span className="text-muted-foreground text-sm truncate max-w-[200px] block" title={row.original.description ?? ''}>
          {row.original.description || '—'}
        </span>
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
            editing ? 'Edit transition rule' : 'Create transition rule'
          }
          maxWidth="max-w-lg"
        >
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSubmit()
            }}
          >
            <div className="space-y-4">
              {formError && <FormError message={formError} />}

              <FormField label="Event type" required hint="The event type this rule applies to (e.g. payment_received).">
                <FormInput
                  value={event_type}
                  onChange={(e) => setEventType(e.target.value)}
                  placeholder="e.g. payment_received"
                  disabled={!!editing}
                />
              </FormField>

              <FormField
                label="Required prior event types"
                hint="Comma- or newline-separated list of event types that must exist before this one."
                required
              >
                <FormTextarea
                  value={requiredPriorInput}
                  onChange={(e) => setRequiredPriorInput(e.target.value)}
                  placeholder="e.g. order_created, quote_sent"
                  rows={3}
                  className="font-mono text-sm"
                />
              </FormField>

              <FormField label="Description" hint="Optional note for this rule.">
                <FormInput
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional"
                />
              </FormField>
            </div>

            <FormModalActions
              onCancel={closeModal}
              submitLabel={editing ? 'Save' : 'Create'}
              loadingLabel={editing ? 'Saving...' : 'Creating...'}
              loading={saving}
            />
          </form>
        </Modal>
      )}

      {deleting && (
        <ConfirmModal
          isOpen={true}
          onClose={() => setDeleting(null)}
          title="Delete transition rule?"
          message="This rule will no longer enforce order for this event type."
          confirmText="Delete"
          cancelText="Cancel"
          isDestructive={true}
          details={{
            'Event type': deleting.event_type,
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
            Event transition rules
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Require that certain event types exist before creating another (e.g. payment only after order).
          </p>
        </div>
        <Button variant="primary" size="md" onClick={openCreate}>
          <Plus className="w-4 h-4" />
          Rule
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
          title: 'No transition rules yet',
          description:
            'Add a rule to enforce event order (e.g. payment_received only after order_created).',
          action: (
            <Button onClick={openCreate} variant="primary" size="md">
              <Plus className="w-4 h-4" />
              Rule
            </Button>
          ),
        }}
      />
    </>
  )
}
