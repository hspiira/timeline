import type { ReactNode } from 'react'
import { useEffect, useId } from 'react'
import { X } from 'lucide-react'
import { Button } from './button'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: ReactNode
  footer?: ReactNode
  maxWidth?: string
  zIndex?: number
  closeButton?: boolean
}

// Add animation styles
const animationStyles = `
  @keyframes modalBackdropEnter {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  @keyframes modalContentEnter {
    from {
      opacity: 0;
      transform: scale(0.95);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }

  .modal-backdrop-animate {
    animation: modalBackdropEnter 150ms ease-out;
  }

  .modal-content-animate {
    animation: modalContentEnter 150ms ease-out;
  }
`

// Inject styles once
if (typeof document !== 'undefined') {
  const styleId = 'modal-animations'
  if (!document.getElementById(styleId)) {
    const style = document.createElement('style')
    style.id = styleId
    style.textContent = animationStyles
    document.head.appendChild(style)
  }
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  footer,
  maxWidth = 'max-w-md',
  zIndex = 50,
  closeButton = true,
}: ModalProps) {
  const titleId = useId()

  // Handle Escape key to close modal
  useEffect(() => {
    if (!isOpen) return

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (!isOpen) return

    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.body.style.overflow = originalOverflow
    }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div
      className="modal-backdrop-animate fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-(--z-index)"
      style={{ '--z-index': zIndex } as any}
      role="presentation"
    >
      <div
        className={`modal-content-animate bg-background border border-border rounded-xs ${maxWidth} w-full max-h-[90vh] overflow-auto p-4 sm:p-6 shadow-2xl`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
      >
        {/* Header */}
        {(title || closeButton) && (
          <div className="flex items-center justify-between mb-6">
            {title && <h2 id={titleId} className="text-xl font-semibold text-foreground">{title}</h2>}
            {closeButton && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="relative -mr-2 -mt-2"
                aria-label="Close modal"
              >
                <X className="w-5 h-5" />
              </Button>
            )}
          </div>
        )}

        {/* Content */}
        <div className="text-foreground">{children}</div>

        {/* Footer */}
        {footer && <div className="pt-4 border-t border-border mt-6">{footer}</div>}
      </div>
    </div>
  )
}

interface ModalActionsProps {
  children: ReactNode
}

export function ModalActions({ children }: ModalActionsProps) {
  return <div className="flex items-center gap-3">{children}</div>
}
