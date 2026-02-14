import { useCallback, useEffect, useState } from 'react'
import { Download, Trash2, FileIcon, Eye } from 'lucide-react'
import type { ColumnDef } from '@tanstack/react-table'
import { timelineApi } from '@/lib/api-client'
import { getApiErrorMessage } from '@/lib/api-utils'
import { DocumentViewer } from './DocumentViewer'
import { useToast } from '@/hooks/useToast'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import { SkeletonDocumentList } from '@/components/ui/Skeleton'
import { ErrorIcon } from '@/components/ui/icons'
import { Button } from '@/components/ui/button'
import { DataTable } from '@/components/ui/DataTable'
import type { components } from '@/lib/timeline-api'

export interface DocumentListProps {
  subjectId?: string
  eventId?: string
  readOnly?: boolean
  onDelete?: (documentId: string) => void
  onError?: (error: string) => void
  onDocumentsLoaded?: (count: number) => void
}

type Document = components['schemas']['DocumentListItem']

const FILE_ICONS: Record<string, string> = {
  'application/pdf': '📄',
  'image/jpeg': '🖼️',
  'image/png': '🖼️',
  'image/gif': '🖼️',
  'image/webp': '🖼️',
  'text/plain': '📝',
  'application/msword': '📘',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '📘',
  'application/vnd.ms-excel': '📊',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '📊',
}

function getMimeType(doc: Document): string {
  return doc.mime_type || 'application/octet-stream'
}

function getDisplayName(doc: Document): string {
  return doc.filename
}

function getFileSize(doc: Document): number {
  return doc.file_size || 0
}

export function DocumentList({ subjectId, eventId, readOnly, onDelete, onError, onDocumentsLoaded }: DocumentListProps) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [viewingDocument, setViewingDocument] = useState<{ id: string; filename: string; type: string } | null>(null)
  const [confirmingDelete, setConfirmingDelete] = useState<{ id: string; filename: string } | null>(null)
  const toast = useToast()

  // Define columns for DataTable
  const columns: ColumnDef<Document>[] = [
    {
      accessorKey: 'filename',
      header: 'Name',
      cell: ({ row }) => {
        const doc = row.original
        const mimeType = getMimeType(doc)
        const filename = getDisplayName(doc)
        const icon = FILE_ICONS[mimeType] || '📎'

        return (
          <Button
            variant="ghost"
            onClick={() => {
              row.getIsSelected?.() ? null : handleView(doc)
            }}
            className="flex items-center gap-2 text-foreground hover:text-foreground/90 transition-colors cursor-pointer group h-auto p-0"
            title="Click to view"
          >
            <span className="text-sm sm:text-base shrink-0">{icon}</span>
            <span className="truncate underline-offset-2 group-hover:underline font-medium text-foreground">
              {filename}
            </span>
          </Button>
        )
      },
    },
    {
      accessorKey: 'file_size',
      header: 'Size',
      cell: ({ row }) => {
        const size = getFileSize(row.original)
        return (
          <span className="text-muted-foreground whitespace-nowrap">
            {size < 1024 * 1024
              ? `${(size / 1024).toFixed(1)}KB`
              : `${(size / 1024 / 1024).toFixed(2)}MB`}
          </span>
        )
      },
    },
    {
      accessorKey: 'version',
      header: 'Version',
      cell: ({ row }) => (
        <span className="text-muted-foreground text-xs sm:text-sm whitespace-nowrap">
          {row.original.version != null ? `v${row.original.version}` : '—'}
        </span>
      ),
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => {
        const doc = row.original
        return (
          <div className="flex items-center justify-end gap-0.5 sm:gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleView(doc)}
              title="View document"
            >
              <Eye className="w-3 sm:w-4 h-3 sm:h-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleDownload(doc.id, getDisplayName(doc))}
              title="Download"
            >
              <Download className="w-3 sm:w-4 h-3 sm:h-4" />
            </Button>
            {!readOnly && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleDeleteClick(doc.id, getDisplayName(doc))}
                disabled={deleting === doc.id}
                title="Delete"
                isLoading={deleting === doc.id}
              >
                {deleting !== doc.id && <Trash2 className="w-3 sm:w-4 h-3 sm:h-4 text-destructive" />}
              </Button>
            )}
          </div>
        )
      },
    },
  ]

  const fetchDocuments = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      let response

      if (subjectId) {
        response = await timelineApi.documents.listBySubject(subjectId)
      } else if (eventId) {
        response = await timelineApi.documents.listByEvent(eventId)
      } else {
        return
      }

      if (response.error) {
        const errorMsg = getApiErrorMessage(response.error, 'Failed to load documents')
        setError(errorMsg)
        onError?.(errorMsg)
      } else if (response.data && Array.isArray(response.data)) {
        setDocuments(response.data)
        onDocumentsLoaded?.(response.data.length)
      } else {
        setDocuments([])
        onDocumentsLoaded?.(0)
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unexpected error loading documents'
      setError(errorMsg)
      onError?.(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [subjectId, eventId, onError, onDocumentsLoaded])

  useEffect(() => {
    if (subjectId || eventId) {
      fetchDocuments()
    }
  }, [subjectId, eventId, fetchDocuments])

  const handleDeleteClick = (documentId: string, filename: string) => {
    setConfirmingDelete({ id: documentId, filename })
  }

  const handleConfirmDelete = async () => {
    if (!confirmingDelete) return

    const { id: documentId, filename } = confirmingDelete
    setDeleting(documentId)

    try {
      const { error: deleteError } = await timelineApi.documents.delete(documentId)

      if (deleteError) {
        const errorMsg = getApiErrorMessage(deleteError, 'Failed to delete document')
        setError(errorMsg)
        onError?.(errorMsg)
        toast.error('Failed to delete', errorMsg)
        throw new Error(errorMsg)
      }

      setDocuments((prev) => prev.filter((doc) => doc.id !== documentId))
      onDelete?.(documentId)
      toast.success('Document deleted', `"${filename}" has been removed`)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unexpected error deleting document'
      setError(errorMsg)
      onError?.(errorMsg)
      toast.error('Failed to delete', errorMsg)
      throw err
    } finally {
      setDeleting(null)
    }
  }

  const handleView = (doc: Document) => {
    const mimeType = getMimeType(doc)
    const filename = getDisplayName(doc)
    setViewingDocument({
      id: doc.id,
      filename,
      type: mimeType,
    })
  }

  const handleDownload = async (documentId: string, filename: string) => {
    try {
      const { data, error: downloadError } = await timelineApi.documents.download(documentId)

      if (downloadError) {
        const errorMsg = getApiErrorMessage(downloadError, 'Failed to download document')
        setError(errorMsg)
        onError?.(errorMsg)
        return
      }

      if (data?.url) {
        const a = document.createElement('a')
        a.href = data.url
        a.download = filename
        a.target = '_blank'
        a.rel = 'noopener noreferrer'
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to download'
      setError(errorMsg)
      onError?.(errorMsg)
    }
  }

  if (loading) {
    return <SkeletonDocumentList />
  }

  if (error && documents.length === 0) {
    return (
      <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-none flex gap-3">
        <ErrorIcon className="text-destructive mt-0.5" />
        <div>
          <h3 className="font-semibold text-foreground text-sm">Error loading documents</h3>
          <p className="text-xs text-muted-foreground">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <DataTable
        data={documents}
        columns={columns}
        isLoading={loading}
        isEmpty={documents.length === 0}
        variant="documents"
        enablePagination={true}
        pageSize={10}
        emptyState={{
          icon: FileIcon,
          title: 'No documents yet',
          description: 'Documents will appear here once they are uploaded to this subject',
        }}
      />

      {/* Document Viewer Modal */}
      {viewingDocument && (
        <DocumentViewer
          documentId={viewingDocument.id}
          filename={viewingDocument.filename}
          fileType={viewingDocument.type}
          onClose={() => setViewingDocument(null)}
        />
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmModal
        isOpen={!!confirmingDelete}
        onClose={() => setConfirmingDelete(null)}
        title="Delete Document?"
        message={`Are you sure you want to delete "${confirmingDelete?.filename}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        isDestructive={true}
        onConfirm={handleConfirmDelete}
      />
    </>
  )
}
