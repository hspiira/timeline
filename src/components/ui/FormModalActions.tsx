import { Button } from './button'
import { LoadingIcon } from './icons'

export interface FormModalActionsProps {
  submitLabel: string
  /** Shown on submit button when loading (e.g. "Creating...", "Updating...") */
  loadingLabel: string
  cancelLabel?: string
  onCancel: () => void
  loading: boolean
  /** Optional: disable submit (e.g. when validation fails) */
  submitDisabled?: boolean
}

export function FormModalActions({
  submitLabel,
  loadingLabel,
  cancelLabel = 'Cancel',
  onCancel,
  loading,
  submitDisabled = false,
}: FormModalActionsProps) {
  return (
    <div className="flex items-center gap-3 mt-6">
      <Button
        type="submit"
        disabled={loading || submitDisabled}
        className="flex-1"
      >
        {loading ? (
          <>
            <LoadingIcon />
            {loadingLabel}
          </>
        ) : (
          submitLabel
        )}
      </Button>
      <Button
        type="button"
        onClick={onCancel}
        disabled={loading}
        variant="outline"
        className="flex-1"
      >
        {cancelLabel}
      </Button>
    </div>
  )
}
