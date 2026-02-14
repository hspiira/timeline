import { useState } from 'react'
import { useToast } from '@/hooks/useToast'
import { useFormSubmit } from '@/hooks/useFormSubmit'
import { FormField, FormInput, FormError } from '@/components/ui/FormField'
import { FormModalActions } from '@/components/ui/FormModalActions'
import { Modal } from '@/components/ui/Modal'
import { validateAlphanumericUnderscore } from '@/lib/validation'

interface CreateSubjectModalProps {
  isOpen: boolean
  onClose: () => void
  onCreate: (subjectType: string, externalRef?: string) => Promise<boolean>
}

export function CreateSubjectModal({
  isOpen,
  onClose,
  onCreate,
}: CreateSubjectModalProps) {
  const [subjectType, setSubjectType] = useState('')
  const [externalRef, setExternalRef] = useState('')
  const { execute, loading, error, setError } = useFormSubmit()
  const toast = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const validationError = validateAlphanumericUnderscore(subjectType, 'Subject type')
    if (validationError) {
      setError(validationError)
      toast.error('Validation error', validationError)
      return
    }

    const success = await execute(() =>
      onCreate(subjectType.toLowerCase(), externalRef || undefined)
    )

    if (success) {
      setSubjectType('')
      setExternalRef('')
      onClose()
    } else {
      const createError = 'Failed to create subject. Please try again.'
      setError(createError)
    }
  }

  if (!isOpen) return null

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Create Subject"
      maxWidth="max-w-md"
    >
      <form onSubmit={handleSubmit}>
        <div className="space-y-4">
          {error && <FormError message={error} />}

          {/* Subject Type */}
          <FormField
            label="Subject Type"
            required
            hint="Alphanumeric characters and underscores only"
          >
            <FormInput
              type="text"
              value={subjectType}
              onChange={(e) => setSubjectType(e.target.value)}
              placeholder="e.g., user, order, project"
              disabled={loading}
              autoFocus
            />
          </FormField>

          {/* External Reference */}
          <FormField
            label="External Reference"
            hint="Optional - leave blank if not needed"
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

        <FormModalActions
          submitLabel="Create Subject"
          loadingLabel="Creating..."
          onCancel={onClose}
          loading={loading}
        />
      </form>
    </Modal>
  )
}
