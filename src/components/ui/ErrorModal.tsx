import { AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Modal } from '@/components/ui/Modal'

export interface ErrorModalProps {
  /** When true, the modal is visible. */
  open: boolean
  /** Called when the user dismisses (close button or backdrop). */
  onClose: () => void
  /** Short title, e.g. "Error". */
  title?: string
  /** Main error message to show. */
  message: string
}

export function ErrorModal({ open, onClose, title = 'Error', message }: ErrorModalProps) {
  return (
    <Modal
      isOpen={open}
      onClose={onClose}
      title={title}
      maxWidth="max-w-md"
      closeButton={true}
      footer={
        <Button type="button" variant="primary" onClick={onClose}>
          OK
        </Button>
      }
    >
      <div className="flex gap-3">
        <div className="shrink-0 w-10 h-10 rounded-full bg-destructive/10 flex items-center justify-center">
          <AlertCircle className="w-5 h-5 text-destructive" />
        </div>
        <p className="text-sm text-foreground pt-1">{message}</p>
      </div>
    </Modal>
  )
}
