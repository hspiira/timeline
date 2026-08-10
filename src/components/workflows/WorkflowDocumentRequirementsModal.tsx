import { useState, useEffect } from 'react'
import { timelineApi } from '@/lib/api-client'
import { FileCheck, Plus, Trash2 } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/button'
import { SingleSelectCombobox } from '@/components/ui/combobox'
import { Input } from '@/components/ui/input'
import { LoadingIcon } from '@/components/ui/icons'
import type { components } from '@/lib/timeline-api'

type DocumentRequirement = components['schemas']['DocumentRequirementResponse']
type DocumentCategoryListItem = components['schemas']['DocumentCategoryListItem']

interface Props {
  workflowId: string
  workflowName: string
  isOpen: boolean
  onClose: () => void
}

export function WorkflowDocumentRequirementsModal({
  workflowId,
  workflowName,
  isOpen,
  onClose,
}: Props) {
  const [requirements, setRequirements] = useState<DocumentRequirement[]>([])
  const [categories, setCategories] = useState<DocumentCategoryListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [addCategoryId, setAddCategoryId] = useState('')
  const [addMinCount, setAddMinCount] = useState(1)
  const [adding, setAdding] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen || !workflowId) return
    let cancelled = false
    setLoading(true)
    Promise.all([
      timelineApi.workflows.documentRequirements.list(workflowId),
      timelineApi.documentCategories.list({ skip: 0, limit: 500 }),
    ]).then(([reqRes, catRes]) => {
      if (cancelled) return
      setRequirements(Array.isArray(reqRes.data) ? reqRes.data : [])
      setCategories(Array.isArray(catRes.data) ? catRes.data : [])
      setLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [isOpen, workflowId])

  const categoryOptions = categories.map((c) => ({
    value: c.id,
    label: c.display_name || c.category_name || c.id,
  }))

  const existingCategoryIds = new Set(requirements.map((r) => r.document_category_id))
  const availableOptions = [
    { value: '', label: 'Select category' },
    ...categoryOptions.filter((o) => !existingCategoryIds.has(o.value)),
  ]

  const handleAdd = async () => {
    if (!addCategoryId || addMinCount < 1) return
    setAdding(true)
    const { data, error } =
      await timelineApi.workflows.documentRequirements.create(workflowId, {
        document_category_id: addCategoryId,
        min_count: addMinCount,
      })
    setAdding(false)
    if (error) return
    if (data) {
      setRequirements((prev) => [...prev, data])
      setAddCategoryId('')
      setAddMinCount(1)
    }
  }

  const handleDelete = async (requirementId: string) => {
    setDeletingId(requirementId)
    const { error } =
      await timelineApi.workflows.documentRequirements.delete(requirementId)
    setDeletingId(null)
    if (error) return
    setRequirements((prev) => prev.filter((r) => r.id !== requirementId))
  }

  const categoryName = (id: string) =>
    categories.find((c) => c.id === id)?.display_name ||
    categories.find((c) => c.id === id)?.category_name ||
    id

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Document requirements"
      maxWidth="max-w-2xl"
    >
      <div className="space-y-4">
        {loading ? (
          <div className="flex items-center gap-2 text-muted-foreground py-4">
            <LoadingIcon />
            Loading...
          </div>
        ) : (
          <>
            <p className="text-sm text-muted-foreground">
              For workflow <span className="font-medium text-foreground">{workflowName}</span>: require documents by category before flows can proceed. Add categories and minimum counts below.
            </p>

            <div className="flex flex-wrap items-end gap-2">
              <div className="flex-1 min-w-[200px]">
                <label className="block text-sm font-medium text-foreground mb-1">
                  Document category
                </label>
                <SingleSelectCombobox
                  value={addCategoryId}
                  onValueChange={setAddCategoryId}
                  options={availableOptions}
                  placeholder="Select category"
                  clearable
                />
              </div>
              <div className="w-24">
                <label className="block text-sm font-medium text-foreground mb-1">
                  Min count
                </label>
                <Input
                  type="number"
                  min={1}
                  value={addMinCount}
                  onChange={(e) =>
                    setAddMinCount(Math.max(1, parseInt(e.target.value, 10) || 1))
                  }
                />
              </div>
              <Button
                size="sm"
                disabled={!addCategoryId || adding}
                onClick={handleAdd}
              >
                {adding ? <LoadingIcon /> : <Plus className="w-4 h-4" />}
                Add
              </Button>
            </div>

            <div>
              <h3 className="text-sm font-medium text-foreground mb-2">
                Required categories ({requirements.length})
              </h3>
              {requirements.length === 0 ? (
                <p className="text-sm text-muted-foreground py-3 px-3 bg-muted/30 rounded-none border border-border/50">
                  No document requirements yet. Select a category above and click Add.
                </p>
              ) : (
                <ul
                  className="list-none border border-border/50 rounded-none divide-y divide-border/30 max-h-[240px] overflow-y-auto"
                  role="list"
                >
                  {requirements.map((r) => (
                    <li
                      key={r.id}
                      className="flex items-center justify-between px-3 py-2"
                    >
                      <span className="text-sm">
                        {categoryName(r.document_category_id)} (min: {r.min_count})
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-muted-foreground hover:text-destructive"
                        disabled={deletingId === r.id}
                        onClick={() => handleDelete(r.id)}
                      >
                        {deletingId === r.id ? (
                          <LoadingIcon />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}
      </div>
    </Modal>
  )
}
