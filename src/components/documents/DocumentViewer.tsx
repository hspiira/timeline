import { useEffect, useMemo, useState } from 'react'
import { Download, Printer, File as FileIcon, X } from 'lucide-react'
import { timelineApi } from '@/lib/api-client'
import { getApiErrorMessage } from '@/lib/api-utils'
import { LoadingIcon, ErrorIcon } from '@/components/ui/icons'
import { Button } from '@/components/ui/button'

export interface DocumentViewerProps {
  documentId: string
  filename: string
  fileType: string
  onClose: () => void
}

type ViewerState = 'loading' | 'ready' | 'error'

/** API may return { url, expires_in_hours } (signed URL) or inline content. */
function isDownloadUrlResponse(
  data: unknown
): data is { url: string; expires_in_hours?: number } {
  return (
    typeof data === 'object' &&
    data !== null &&
    'url' in data &&
    typeof (data as { url: unknown }).url === 'string'
  )
}

export function DocumentViewer({ documentId, filename, fileType, onClose }: DocumentViewerProps) {
  const [state, setState] = useState<ViewerState>('loading')
  const [error, setError] = useState<string | null>(null)
  const [content, setContent] = useState<Blob | null>(null)
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)

  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [onClose])

  useEffect(() => {
    const loadDocument = async () => {
      setState('loading')
      setError(null)

      try {
        const { data, error: fetchError } = await timelineApi.documents.download(documentId)

        if (fetchError) {
          setError(getApiErrorMessage(fetchError, 'Failed to load document'))
          setState('error')
          return
        }

        if (data) {
          // API returns { url, expires_in_hours } for download-url endpoint
          if (isDownloadUrlResponse(data)) {
            setDownloadUrl(data.url)
            setContent(null)
            setState('ready')
            return
          }
          // Inline content (legacy or different endpoint)
          if (data instanceof Blob) {
            setContent(data)
            setDownloadUrl(null)
            setState('ready')
          } else if (data instanceof ArrayBuffer) {
            const blob = new Blob([data], { type: fileType || 'application/octet-stream' })
            setContent(blob)
            setDownloadUrl(null)
            setState('ready')
          } else if (typeof data === 'string') {
            const blob = new Blob([data], { type: fileType || 'application/octet-stream' })
            setContent(blob)
            setDownloadUrl(null)
            setState('ready')
          } else {
            const blob = new Blob([JSON.stringify(data)], { type: 'application/json' })
            setContent(blob)
            setDownloadUrl(null)
            setState('ready')
          }
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Unexpected error loading document'
        setError(errorMsg)
        setState('error')
      }
    }

    loadDocument()
  }, [documentId, fileType])

  const isImage = fileType.startsWith('image/')
  const isPdf = fileType === 'application/pdf'
  const isPreviewable = isImage || isPdf
  // When API returned a URL, use it for preview (image/iframe) or show download; do not create object URL from blob
  const imageUrl = useMemo(() => {
    if (state === 'ready' && isImage) {
      if (downloadUrl) return downloadUrl
      if (content instanceof Blob) return URL.createObjectURL(content)
    }
    return undefined
  }, [state, isImage, content, downloadUrl])

  useEffect(() => {
    return () => {
      if (imageUrl && content instanceof Blob) {
        URL.revokeObjectURL(imageUrl)
      }
    }
  }, [imageUrl, content])

  const handleDownload = () => {
    if (downloadUrl) {
      const a = document.createElement('a')
      a.href = downloadUrl
      a.download = filename
      a.rel = 'noopener noreferrer'
      a.target = '_blank'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      return
    }
    if (content instanceof Blob) {
      const url = window.URL.createObjectURL(content)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    }
  }

  const handlePrint = () => {
    if (isImage && content instanceof Blob) {
      const url = URL.createObjectURL(content)
      const printWindow = window.open(url)
      if (printWindow) {
        printWindow.addEventListener('load', () => {
          printWindow.print()
        })
      }
    }
  }

  // Note: DocumentViewer doesn't use the standard Modal since it needs custom header layout
  // We keep the direct DOM structure for better control over the flex layout
  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose} role="presentation">
      <div
        className="bg-background border border-border rounded-none shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="document-viewer-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex-1 min-w-0">
            <h2 id="document-viewer-title" className="font-semibold text-foreground truncate">{filename}</h2>
            <p className="text-xs text-muted-foreground">{fileType}</p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {isImage && (
              <Button variant="ghost" size="sm" onClick={handlePrint} title="Print">
                <Printer className="w-4 h-4" />
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={handleDownload} title="Download">
              <Download className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={onClose} title="Close" aria-label="Close modal">
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-auto flex items-center justify-center bg-muted/20">
          {state === 'loading' && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <LoadingIcon size="lg" />
              <span>Loading document...</span>
            </div>
          )}

          {state === 'error' && (
            <div className="flex flex-col items-center gap-3 text-center p-8">
              <ErrorIcon className="w-12 h-12 text-red-500" />
              <div>
                <h3 className="font-semibold text-foreground">Unable to load document</h3>
                <p className="text-sm text-muted-foreground mt-1">{error}</p>
                <Button onClick={handleDownload} className="mt-4">
                  Download instead
                </Button>
              </div>
            </div>
          )}

          {state === 'ready' && (
            <>
              {isImage && imageUrl && (
                <img
                  src={imageUrl}
                  alt={filename}
                  className="max-w-full max-h-full object-contain"
                  referrerPolicy="no-referrer"
                />
              )}

              {isPdf && (
                <div className="flex flex-col items-center justify-center gap-4 flex-1 min-h-0 w-full">
                  {downloadUrl ? (
                    <>
                      <iframe
                        src={downloadUrl}
                        title={filename}
                        className="w-full flex-1 min-h-[60vh] border-0 rounded-none"
                        referrerPolicy="no-referrer"
                      />
                      <Button onClick={handleDownload} className="mt-4 shrink-0">
                        Download PDF
                      </Button>
                    </>
                  ) : (
                    <>
                      <FileIcon className="w-16 h-16 text-muted-foreground/50" />
                      <div className="text-center">
                        <p className="text-foreground font-medium">PDF Preview</p>
                        <p className="text-sm text-muted-foreground mt-1">PDF preview is not available in your browser</p>
                        <Button onClick={handleDownload} className="mt-4">
                          Download PDF
                        </Button>
                      </div>
                    </>
                  )}
                </div>
              )}

              {!isPreviewable && (
                <div className="flex flex-col items-center justify-center gap-4">
                  <FileIcon className="w-16 h-16 text-muted-foreground/50" />
                  <div className="text-center">
                    <p className="text-foreground font-medium">File Preview Unavailable</p>
                    <p className="text-sm text-muted-foreground mt-1">This file type cannot be previewed</p>
                    <Button onClick={handleDownload} className="mt-4">
                      Download File
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
