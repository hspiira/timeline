import { useState } from 'react'
import { useToast } from '@/hooks/useToast'
import { FormField, FormInput, FormError } from '@/components/ui/FormField'
import { Button } from '@/components/ui/button'
import { LoadingIcon } from '@/components/ui/icons'
import { Modal } from '@/components/ui/Modal'

interface EditSubjectModalProps {
  isOpen: boolean
  onClose: () => void
  subject: {
    id: string
    subject_type: string
    external_ref?: string | null
  }
  onUpdate: (subjectId: string, externalRef?: string) => Promise<boolean>
}

export function EditSubjectModal({
  isOpen,
  onClose,
  subject,
  onUpdate,
}: EditSubjectModalProps) {
  const [externalRef, setExternalRef] = useState(subject.external_ref || '')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const toast = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    setLoading(true)
    const success = await onUpdate(subject.id, externalRef || undefined)
    setLoading(false)

    if (success) {
      setExternalRef('')
      onClose()
      toast.success('Subject updated', 'Your changes have been saved')
    } else {
      const errorMsg = 'Failed to update subject. Please try again.'
      setError(errorMsg)
      toast.error('Update failed', errorMsg)
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Edit Subject"
      maxWidth="max-w-md"
    >
      <form onSubmit={handleSubmit}>
        <div className="space-y-4">
          {error && <FormError message={error} />}

          {/* Subject Type (Read-only) */}
          <FormField label="Subject Type">
            <div className="px-3 py-2 bg-muted rounded-none text-foreground text-sm">
              {subject.subject_type}
            </div>
          </FormField>

          {/* External Reference */}
          <FormField
            label="External Reference"
            hint="Leave blank to remove the external reference"
          >
            <FormInput
              type="text"
              value={externalRef}
              onChange={(e) => setExternalRef(e.target.value)}
              placeholder="e.g., external ID or reference"
              disabled={loading}
            />
          </FormField>
        </div>

        <div className="flex items-center gap-3 mt-6">
          <Button
            type="submit"
            disabled={loading}
            className="flex-1"
          >
            {loading ? (
              <>
                <LoadingIcon />
                Updating...
              </>
            ) : (
              'Update Subject'
            )}
          </Button>
          <Button
            type="button"
            onClick={onClose}
            disabled={loading}
            variant="outline"
            className="flex-1"
          >
            Cancel
          </Button>
        </div>
      </form>
    </Modal>
  )
}
