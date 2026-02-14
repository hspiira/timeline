import { useEffect, useState } from 'react'
import { AlertTriangle, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LoadingIcon } from '@/components/ui/icons'

export interface DeleteConfirmModalProps {
  isOpen: boolean
  title: string
  message: string
  itemLabel: string
  details?: Record<string, string | number>
  warning?: string
  onConfirm: () => void | Promise<void>
  onClose: () => void
  isDestructive?: boolean
}

export function DeleteConfirmModal({
  isOpen,
  title,
  message,
  itemLabel,
  details,
  warning,
  onConfirm,
  onClose,
  isDestructive = true,
}: DeleteConfirmModalProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setLoading(false)
      setError(null)
    }
  }, [isOpen])

  // Handle Escape key to close modal
  useEffect(() => {
    if (!isOpen) return

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !loading) {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose, loading])

  if (!isOpen) return null

  const handleConfirm = async () => {
    setError(null)
    setLoading(true)

    try {
      await onConfirm()
      onClose()
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'An error occurred'
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={loading ? undefined : onClose}
      role="presentation"
    >
      <div
        className="bg-background border border-border rounded-none max-w-md w-full shadow-xl p-6"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        aria-describedby="modal-description"
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-start gap-3">
            <div className={`w-10 h-10 rounded-none flex items-center justify-center shrink-0 ${
              isDestructive
                ? 'bg-red-100 dark:bg-red-950/30'
                : 'bg-yellow-100 dark:bg-yellow-950/30'
            }`}>
              <AlertTriangle className={`w-5 h-5 ${
                isDestructive
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-yellow-600 dark:text-yellow-400'
              }`} />
            </div>
            <div>
              <h2 id="modal-title" className="text-lg font-semibold text-foreground">{title}</h2>
              <p id="modal-description" className="text-sm text-muted-foreground mt-0.5">{message}</p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            disabled={loading}
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Details */}
        {details && Object.keys(details).length > 0 && (
          <div className="mb-4 p-3 bg-muted/50 rounded-none border border-border/50">
            <div className="space-y-2">
              {Object.entries(details).map(([key, value]) => (
                <div key={key}>
                  <p className="text-xs text-muted-foreground capitalize">{key}</p>
                  <p className="text-sm font-medium text-foreground">{value}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Warning Message */}
        {warning && (
          <div className={`mb-4 p-3 rounded-none border ${
            isDestructive
              ? 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800'
              : 'bg-yellow-50 dark:bg-yellow-950/20 border-yellow-200 dark:border-yellow-800'
          }`}>
            <p className={`text-xs ${
              isDestructive
                ? 'text-red-900 dark:text-red-200'
                : 'text-yellow-900 dark:text-yellow-200'
            }`}>
              {warning}
            </p>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-none">
            <p className="text-xs text-red-900 dark:text-red-200 font-medium">Error</p>
            <p className="text-xs text-red-800 dark:text-red-300 mt-1">{error}</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2 border-t border-border">
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            disabled={loading}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            variant={isDestructive ? 'destructive' : 'primary'}
            size="sm"
            onClick={handleConfirm}
            disabled={loading}
            isLoading={loading}
            className="flex-1"
          >
            {loading ? (
              <>
                <LoadingIcon size="sm" />
                <span>Confirming...</span>
              </>
            ) : (
              `Confirm ${itemLabel}`
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}

// Export with schema-specific name for backward compatibility
export { DeleteConfirmModal as DeleteSchemaModal }
