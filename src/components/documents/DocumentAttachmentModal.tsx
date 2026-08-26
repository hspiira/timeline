import { X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { ErrorIcon } from '@/components/ui/icons'
import { DocumentList } from './DocumentList'
import { DocumentUpload } from './DocumentUpload'

interface DocumentAttachmentModalProps {
  isOpen: boolean
  onClose: () => void
  eventId: string
  subjectId?: string
  eventType: string
}

type Tab = 'upload' | 'attached'

export function DocumentAttachmentModal({
  isOpen,
  onClose,
  eventId,
  subjectId,
  eventType,
}: DocumentAttachmentModalProps) {
  const [activeTab, setActiveTab] = useState<Tab>('upload')
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

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

  if (!isOpen) return null

  const handleUploadComplete = () => {
    setUploadError(null)
    // Refresh the document list
    setRefreshKey((prev) => prev + 1)
    // Optionally switch to viewing attached documents
    setActiveTab('attached')
  }

  const handleUploadError = (error: string) => {
    setUploadError(error)
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      role="presentation"
      onClick={onClose}
    >
      <div
        className="bg-background border border-border rounded-none max-w-2xl w-full max-h-[90vh] overflow-auto p-6 shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 id="modal-title" className="text-xl font-semibold text-foreground">
              Attach Documents
            </h2>
            <p className="text-xs text-muted-foreground mt-1">
              Event: {eventType} {eventId.slice(0, 8)}...
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close modal">
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-4 border-b border-border">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setActiveTab('upload')}
            className={`text-xs font-medium transition-colors border-b-2 rounded-none ${
              activeTab === 'upload'
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            Upload Documents
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setActiveTab('attached')}
            className={`text-xs font-medium transition-colors border-b-2 rounded-none ${
              activeTab === 'attached'
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            Attached Documents
          </Button>
        </div>

        {/* Error Alert */}
        {uploadError && (
          <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 rounded-none flex items-center gap-2">
            <ErrorIcon size="md" className="text-destructive" />
            <p className="text-sm text-destructive">
              {typeof uploadError === 'string' ? uploadError : JSON.stringify(uploadError)}
            </p>
          </div>
        )}

        {/* Content */}
        {activeTab === 'upload' && (
          <div className="space-y-4">
            {!subjectId && (
              <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-none text-sm text-amber-800 dark:text-amber-300">
                Document upload requires a subject. This event may not have an associated subject.
              </div>
            )}
            <DocumentUpload
              subjectId={subjectId}
              eventId={eventId}
              onUploadComplete={handleUploadComplete}
              onError={handleUploadError}
            />
          </div>
        )}

        {activeTab === 'attached' && (
          <div>
            <DocumentList key={refreshKey} eventId={eventId} subjectId={subjectId} />
          </div>
        )}

        {/* Close Button */}
        <div className="mt-6 pt-4 border-t border-border">
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  )
}
