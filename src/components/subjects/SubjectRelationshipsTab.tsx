import { useState, useEffect, useCallback } from 'react'
import { Link } from '@tanstack/react-router'
import { timelineApi } from '@/lib/api-client'
import { formatDateTimeSafe } from '@/lib/format-date'
import { Button } from '@/components/ui/button'
import { FormField } from '@/components/ui/FormField'
import { SingleSelectCombobox } from '@/components/ui/combobox'
import SubjectSelector from '@/components/subjects/SubjectSelector'
import { EmptyState } from '@/components/ui/EmptyState'
import { Link2, Plus, Trash2 } from 'lucide-react'
import type { components } from '@/lib/timeline-api'

type SubjectRelationshipListItem = components['schemas']['SubjectRelationshipListItem']
type RelationshipKindListItem = components['schemas']['RelationshipKindListItem']

interface SubjectRelationshipsTabProps {
  subjectId: string
  subjectDisplayName?: string | null
}

export function SubjectRelationshipsTab({
  subjectId,
  subjectDisplayName,
}: SubjectRelationshipsTabProps) {
  const [relationships, setRelationships] = useState<SubjectRelationshipListItem[]>([])
  const [kinds, setKinds] = useState<RelationshipKindListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)
  const [targetSubjectId, setTargetSubjectId] = useState('')
  const [relationshipKind, setRelationshipKind] = useState('')
  const [addError, setAddError] = useState<string | null>(null)
  const [removing, setRemoving] = useState<string | null>(null)

  const fetchRelationships = useCallback(async () => {
    const res = await timelineApi.subjects.listRelationships(subjectId, {
      as_source: true,
      as_target: true,
    })
    if (res.error) {
      setError('Failed to load relationships')
      return
    }
    const data = res.data as SubjectRelationshipListItem[] | undefined
    setRelationships(Array.isArray(data) ? data : [])
  }, [subjectId])

  const fetchKinds = useCallback(async () => {
    const res = await timelineApi.relationshipKinds.list()
    if (res.error) return
    const data = res.data as RelationshipKindListItem[] | undefined
    setKinds(Array.isArray(data) ? data : [])
  }, [])

  useEffect(() => {
    if (!subjectId) return
    setLoading(true)
    setError(null)
    Promise.all([fetchRelationships(), fetchKinds()]).finally(() => setLoading(false))
  }, [subjectId, fetchRelationships, fetchKinds])

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    setAddError(null)
    if (!targetSubjectId.trim() || !relationshipKind.trim()) {
      setAddError('Select a subject and relationship kind')
      return
    }
    setAdding(true)
    const res = await timelineApi.subjects.addRelationship(subjectId, {
      target_subject_id: targetSubjectId.trim(),
      relationship_kind: relationshipKind.trim(),
    })
    setAdding(false)
    if (res.error) {
      const msg =
        typeof res.error === 'object' && res.error && 'detail' in res.error
          ? String((res.error as { detail: unknown }).detail)
          : 'Failed to add relationship'
      setAddError(msg)
      return
    }
    setTargetSubjectId('')
    setRelationshipKind('')
    fetchRelationships()
  }

  const handleRemove = async (rel: SubjectRelationshipListItem) => {
    const sourceId = rel.source_subject_id
    const targetId = rel.target_subject_id
    const kind = rel.relationship_kind
    setRemoving(rel.id)
    const res = await timelineApi.subjects.removeRelationship(sourceId, {
      target_subject_id: targetId,
      relationship_kind: kind,
    })
    setRemoving(null)
    if (!res.error) fetchRelationships()
  }

  const kindOptions = kinds.length
    ? kinds.map((k) => ({ value: k.kind, label: k.display_name || k.kind }))
    : []
  const kindSelectOptions =
    kindOptions.length > 0
      ? [{ value: '', label: 'Select kind' }, ...kindOptions]
      : []

  if (loading) {
    return (
      <div className="bg-card/80 backdrop-blur-sm rounded-none p-8 border border-border/30 text-center text-muted-foreground text-sm">
        Loading relationships…
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-card/80 backdrop-blur-sm rounded-none p-8 border border-border/30 text-center text-destructive text-sm">
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Add relationship */}
      <section className="bg-card/80 backdrop-blur-sm rounded-none border border-border/30 overflow-hidden">
        <div className="border-l-2 border-primary/80 bg-muted/20 px-4 py-3 flex items-center gap-2">
          <Plus className="w-4 h-4 text-primary shrink-0" />
          <span className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
            Add relationship
          </span>
        </div>
        <form onSubmit={handleAdd} className="p-4 space-y-4">
          {addError && (
            <p className="text-sm text-destructive" role="alert">
              {addError}
            </p>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="Target subject" required>
              <SubjectSelector
                value={targetSubjectId}
                onChange={setTargetSubjectId}
                excludeSubjectId={subjectId}
              />
            </FormField>
            <FormField
              label="Relationship kind"
              required
              hint={
                kinds.length === 0
                  ? 'Define kinds in Settings → Relationship kinds, or enter any label'
                  : undefined
              }
            >
              {kinds.length > 0 ? (
                <SingleSelectCombobox
                  value={relationshipKind}
                  onValueChange={setRelationshipKind}
                  options={kindSelectOptions}
                  placeholder="Select kind"
                  clearable
                />
              ) : (
                <input
                  type="text"
                  value={relationshipKind}
                  onChange={(e) => setRelationshipKind(e.target.value)}
                  placeholder="e.g. client_of, parent_of"
                  className="w-full rounded-none border border-input bg-background px-3 py-2 text-sm"
                />
              )}
            </FormField>
          </div>
          <Button type="submit" variant="primary" size="sm" disabled={adding}>
            {adding ? 'Adding…' : 'Add relationship'}
          </Button>
        </form>
      </section>

      {/* List */}
      <section className="bg-card/80 backdrop-blur-sm rounded-none border border-border/30 overflow-hidden">
        <div className="border-l-2 border-border/50 bg-muted/15 px-4 py-3 flex items-center gap-2">
          <Link2 className="w-4 h-4 text-muted-foreground shrink-0" />
          <span className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
            Relationships
          </span>
        </div>
        <div className="p-4">
          {relationships.length === 0 ? (
            <EmptyState
              icon={Link2}
              title="No relationships"
              description="Add a link to another subject using the form above. Relationships appear on both subjects’ timelines as events."
            />
          ) : (
            <ul className="space-y-2">
              {relationships.map((rel) => {
                const isSource = rel.source_subject_id === subjectId
                const otherId = isSource ? rel.target_subject_id : rel.source_subject_id
                return (
                  <li
                    key={rel.id}
                    className="flex items-center justify-between gap-3 py-2 px-3 rounded-none bg-muted/20 border border-border/30"
                  >
                    <div className="min-w-0 flex-1 flex items-center gap-2">
                      <span className="text-xs text-muted-foreground shrink-0">
                        {isSource ? '→' : '←'}
                      </span>
                      <Link
                        to="/subjects/$subjectId"
                        params={{ subjectId: otherId }}
                        search={{ tab: 'events' }}
                        className="text-sm font-mono text-[var(--dashboard-accent)] hover:underline truncate"
                      >
                        {otherId}
                      </Link>
                      <span className="text-xs text-muted-foreground shrink-0">
                        {rel.relationship_kind}
                      </span>
                      <span className="text-xs text-muted-foreground tabular-nums">
                        {formatDateTimeSafe(rel.created_at)}
                      </span>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemove(rel)}
                      disabled={removing === rel.id}
                      className="shrink-0 text-destructive hover:text-destructive"
                      title="Remove relationship"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </section>
    </div>
  )
}
