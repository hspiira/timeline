import { createFileRoute } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { timelineApi } from '@/lib/api-client'
import { useEventTypes } from '@/hooks/useEventTypes'
import { optionsFromStrings } from '@/components/ui/combobox'
import { Plus, Pencil, Trash2, ArrowRight, GitBranch, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Modal } from '@/components/ui/Modal'
import { FormField, FormInput, FormError } from '@/components/ui/FormField'
import { FormModalActions } from '@/components/ui/FormModalActions'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import { ErrorModal } from '@/components/ui/ErrorModal'
import { SingleSelectCombobox } from '@/components/ui/combobox'
import { Input } from '@/components/ui/input'
import { getApiErrorMessage } from '@/lib/api-utils'
import { LoadingIcon } from '@/components/ui/icons'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/settings/event-transition-rules/')({
  component: EventTransitionRulesPage,
})

type EventTransitionRuleResponse = components['schemas']['EventTransitionRuleResponse']
type EventTransitionRuleCreateRequest =
  components['schemas']['EventTransitionRuleCreateRequest']
type EventTransitionRuleUpdate =
  components['schemas']['EventTransitionRuleUpdate']

/** Single rule as a flow card: [prior] [prior] → [target] */
function RuleCard({
  rule,
  onEdit,
  onDelete,
}: {
  rule: EventTransitionRuleResponse
  onEdit: (r: EventTransitionRuleResponse) => void
  onDelete: (r: EventTransitionRuleResponse) => void
}) {
  const priors = rule.required_prior_event_types
  const target = rule.event_type

  return (
    <article className="relative rounded-lg border border-border bg-card p-4 shadow-sm transition-shadow hover:shadow-md hover:border-border/80">
      {/* Flow: required first → then allow */}
      <div className="flex flex-wrap items-center gap-2 min-h-[2rem]">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider shrink-0">
          Required first
        </span>
        <div className="flex flex-wrap items-center gap-1.5">
          {priors.length === 0 ? (
            <span className="text-sm text-muted-foreground/70 italic">—</span>
          ) : (
            priors.map((p) => (
              <span
                key={p}
                className="inline-flex items-center px-2.5 py-1 rounded-md bg-muted/80 text-foreground text-sm font-mono border border-border/50"
              >
                {p}
              </span>
            ))
          )}
        </div>
        <ArrowRight className="w-4 h-4 text-muted-foreground shrink-0 mx-0.5" aria-hidden />
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider shrink-0">
          Then allow
        </span>
        <span className="inline-flex items-center px-3 py-1.5 rounded-md bg-primary/12 text-primary font-medium text-sm font-mono border border-primary/25">
          {target}
        </span>
      </div>

      {rule.description?.trim() && (
        <p className="mt-3 text-sm text-muted-foreground line-clamp-2 pl-0">
          {rule.description}
        </p>
      )}

      <div className="mt-3 flex items-center justify-end gap-1 pt-2 border-t border-border/50">
        <Button
          variant="ghost"
          size="sm"
          title="Edit"
          onClick={() => onEdit(rule)}
        >
          <Pencil className="w-4 h-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          title="Delete"
          onClick={() => onDelete(rule)}
        >
          <Trash2 className="w-4 h-4 text-destructive" />
        </Button>
      </div>
    </article>
  )
}

function EventTransitionRulesPage() {
  const authState = useRequireAuth()
  const { types: eventTypes, loading: eventTypesLoading } = useEventTypes()
  const [items, setItems] = useState<EventTransitionRuleResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<EventTransitionRuleResponse | null>(null)
  const [deleting, setDeleting] = useState<EventTransitionRuleResponse | null>(null)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const [event_type, setEventType] = useState('')
  const [requiredPriorList, setRequiredPriorList] = useState<string[]>([])
  const [customPriorInput, setCustomPriorInput] = useState('')
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
    setRequiredPriorList([])
    setCustomPriorInput('')
    setDescription('')
    setFormError(null)
    setShowModal(true)
  }

  const openEdit = (row: EventTransitionRuleResponse) => {
    setEditing(row)
    setEventType(row.event_type)
    setRequiredPriorList([...row.required_prior_event_types])
    setCustomPriorInput('')
    setDescription(row.description ?? '')
    setFormError(null)
    setShowModal(true)
  }

  const addPrior = (type: string) => {
    const t = type.trim()
    if (!t) return
    if (requiredPriorList.includes(t)) return
    setRequiredPriorList((prev) => [...prev, t])
  }

  const removePrior = (type: string) => {
    setRequiredPriorList((prev) => prev.filter((p) => p !== type))
  }

  const closeModal = () => {
    setShowModal(false)
    setEditing(null)
    setFormError(null)
  }

  const handleSubmit = async () => {
    setFormError(null)
    const required_prior_event_types = requiredPriorList
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

  const eventTypeOptions = optionsFromStrings(eventTypes, {
    value: '',
    label: 'Select event type…',
  })

  if (!authState.user) return null

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

              <FormField
                label="Event type"
                required
                hint="The event type this rule applies to (e.g. payment_received)."
              >
                {editing ? (
                  <span className="inline-flex px-3 py-2 rounded-md bg-muted/60 text-foreground font-mono text-sm border border-border">
                    {event_type}
                  </span>
                ) : eventTypes.length > 0 ? (
                  <SingleSelectCombobox
                    value={event_type}
                    onValueChange={setEventType}
                    options={eventTypeOptions}
                    placeholder="e.g. payment_received"
                    disabled={eventTypesLoading}
                    className="min-h-[2.25rem] w-full"
                  />
                ) : (
                  <FormInput
                    value={event_type}
                    onChange={(e) => setEventType(e.target.value)}
                    placeholder="e.g. payment_received"
                    className="font-mono"
                  />
                )}
              </FormField>

              <FormField
                label="Required prior event types"
                hint="At least one. These event types must already exist before the event type above can be created."
                required
              >
                <div className="space-y-2">
                  {/* Selected as removable pills */}
                  {requiredPriorList.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {requiredPriorList.map((p) => (
                        <span
                          key={p}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-muted/80 text-foreground text-sm font-mono border border-border/50"
                        >
                          {p}
                          <button
                            type="button"
                            onClick={() => removePrior(p)}
                            className="p-0.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
                            aria-label={`Remove ${p}`}
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                  {/* Add from event types (exclude target + already added) */}
                  {eventTypes.length > 0 && (
                    <div className="flex flex-wrap items-center gap-2">
                      <SingleSelectCombobox
                        value=""
                        onValueChange={(v) => {
                          if (v) addPrior(v)
                        }}
                        options={[
                          { value: '', label: 'Add from event types…' },
                          ...eventTypes
                            .filter(
                              (t) =>
                                t !== event_type?.trim() &&
                                !requiredPriorList.includes(t)
                            )
                            .map((t) => ({ value: t, label: t })),
                        ]}
                        placeholder="Add from event types…"
                        disabled={eventTypesLoading}
                        className="min-h-[2rem] flex-1 min-w-[140px]"
                      />
                    </div>
                  )}
                  {/* Custom: type and press Enter */}
                  <Input
                    value={customPriorInput}
                    onChange={(e) => setCustomPriorInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        addPrior(customPriorInput)
                        setCustomPriorInput('')
                      }
                    }}
                    placeholder={
                      eventTypes.length > 0
                        ? 'Or type custom and press Enter'
                        : 'Type event types, press Enter after each'
                    }
                    className="font-mono text-sm"
                  />
                </div>
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
              loadingLabel={editing ? 'Saving…' : 'Creating…'}
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

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-foreground flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-muted-foreground" />
            Event transition rules
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Require that certain event types exist before creating another (e.g. payment only after order).
          </p>
        </div>
        <Button variant="primary" size="md" onClick={openCreate}>
          <Plus className="w-4 h-4" />
          Add rule
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center gap-2 py-12 text-muted-foreground">
          <LoadingIcon />
          <span>Loading rules…</span>
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border bg-muted/20 p-10 text-center">
          <p className="font-medium text-foreground">No transition rules yet</p>
          <p className="text-sm text-muted-foreground mt-1 max-w-sm mx-auto">
            Add a rule to enforce event order (e.g. <span className="font-mono text-foreground/90">payment_received</span> only after <span className="font-mono text-foreground/90">order_created</span>).
          </p>
          <Button onClick={openCreate} variant="primary" size="md" className="mt-4">
            <Plus className="w-4 h-4" />
            Add rule
          </Button>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((rule) => (
            <RuleCard
              key={rule.id}
              rule={rule}
              onEdit={openEdit}
              onDelete={setDeleting}
            />
          ))}
        </div>
      )}
    </>
  )
}
