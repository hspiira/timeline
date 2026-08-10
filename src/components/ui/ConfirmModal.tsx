import { useEffect, useState } from 'react'
import { AlertCircle } from 'lucide-react'
import { Modal, ModalActions } from './Modal'
import { Button } from './button'
import { LoadingIcon } from './icons'

export interface ConfirmModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  isDestructive?: boolean
  onConfirm: () => void | Promise<void>
  /** Optional key-value block (e.g. event type, version) */
  details?: Record<string, string | number>
  /** Optional warning message in a highlighted block */
  warning?: string
}

export function ConfirmModal({
  isOpen,
  onClose,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  isDestructive = true,
  onConfirm,
  details,
  warning,
}: ConfirmModalProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      setLoading(false)
      setError(null)
    }
  }, [isOpen])

  const handleConfirm = async () => {
    setError(null)
    setLoading(true)
    try {
      const result = onConfirm()
      if (result instanceof Promise) {
        await result
        onClose()
      } else {
        onClose()
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'An error occurred'
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const iconBg = isDestructive
    ? 'bg-destructive/10 text-destructive'
    : 'bg-amber-100/30 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400'

  const content = (
    <>
      <div className="flex items-start gap-2 mb-4 sm:gap-3">
        <div className={`shrink-0 w-10 h-10 rounded-none flex items-center justify-center ${iconBg}`}>
          <AlertCircle className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-muted-foreground">{message}</p>
        </div>
      </div>

      {details != null && Object.keys(details).length > 0 && (
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

      {warning != null && warning !== '' && (
        <div
          className={`mb-4 p-3 rounded-none border ${
            isDestructive
              ? 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800'
              : 'bg-yellow-50 dark:bg-yellow-950/20 border-yellow-200 dark:border-yellow-800'
          }`}
        >
          <p
            className={`text-xs ${
              isDestructive
                ? 'text-red-900 dark:text-red-200'
                : 'text-yellow-900 dark:text-yellow-200'
            }`}
          >
            {warning}
          </p>
        </div>
      )}

      {error != null && error !== '' && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-none">
          <p className="text-xs text-red-900 dark:text-red-200 font-medium">Error</p>
          <p className="text-xs text-red-800 dark:text-red-300 mt-1">{error}</p>
        </div>
      )}
    </>
  )

  const footer = (
    <ModalActions>
      <Button variant="outline" onClick={onClose} disabled={loading} className="flex-1">
        {cancelText}
      </Button>
      <Button
        variant={isDestructive ? 'destructive' : 'primary'}
        onClick={handleConfirm}
        disabled={loading}
        className="flex-1"
      >
        {loading ? (
          <>
            <LoadingIcon size="sm" />
            <span>Confirming...</span>
          </>
        ) : (
          confirmText
        )}
      </Button>
    </ModalActions>
  )

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => (!loading ? onClose() : undefined)}
      title={title}
      footer={footer}
      closeButton={true}
      maxWidth="max-w-md"
    >
      {content}
    </Modal>
  )
}
