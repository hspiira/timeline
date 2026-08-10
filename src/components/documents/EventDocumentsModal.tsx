import { Plus, X } from 'lucide-react'
import { useEffect, useId, useState } from 'react'
import { timelineApi } from '@/lib/api-client'
import { getApiErrorMessage } from '@/lib/api-utils'
import type { components } from '@/lib/timeline-api'
import { DocumentList } from './DocumentList'
import { EventDocumentUpload } from './EventDocumentUpload'
import { Button } from '@/components/ui/button'
import { SingleSelectCombobox } from '@/components/ui/combobox'
import { JsonSchemaForm } from '@/components/shared/JsonSchemaForm'
import type { JsonSchema } from '@/components/shared/JsonSchemaForm'
import { LoadingIcon } from '@/components/ui/icons'

export interface EventDocumentsModalProps {
  eventId: string
  subjectId: string
  eventType: string
  onClose: () => void
  onDocumentsUpdated?: () => void
}

type DocumentCategoryListItem = components['schemas']['DocumentCategoryListItem']
type DocumentCategoryResponse = components['schemas']['DocumentCategoryResponse']

export function EventDocumentsModal({
  eventId,
  subjectId,
  eventType,
  onClose,
  onDocumentsUpdated
}: EventDocumentsModalProps) {
  const titleId = useId()
  const [showUpload, setShowUpload] = useState(false)
  const [stagedFiles, setStagedFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [categories, setCategories] = useState<DocumentCategoryListItem[]>([])
  const [categoriesLoading, setCategoriesLoading] = useState(false)
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>('')
  const [categoryFull, setCategoryFull] = useState<DocumentCategoryResponse | null>(null)
  const [metadata, setMetadata] = useState<Record<string, unknown>>({})

  // Load document categories when upload section is shown
  useEffect(() => {
    if (!showUpload) return
    let cancelled = false
    setCategoriesLoading(true)
    timelineApi.documentCategories
      .list({ skip: 0, limit: 500 })
      .then(({ data, error: apiError }) => {
        if (cancelled) return
        setCategoriesLoading(false)
        if (!apiError && Array.isArray(data) && data.length > 0) {
          const active = data.filter((c) => c.is_active)
          setCategories(active)
          const first = active[0]
          if (first) setSelectedCategoryId(first.id)
        }
      })
      .catch(() => {
        if (!cancelled) setCategoriesLoading(false)
      })
    return () => { cancelled = true }
  }, [showUpload])

  // Fetch full category when selection changes (for metadata_schema)
  useEffect(() => {
    if (!selectedCategoryId) {
      setCategoryFull(null)
      setMetadata({})
      return
    }
    let cancelled = false
    timelineApi.documentCategories
      .get(selectedCategoryId)
      .then(({ data }) => {
        if (cancelled || !data) return
        setCategoryFull(data)
        setMetadata({})
      })
      .catch(() => {
        if (!cancelled) setCategoryFull(null)
      })
    return () => { cancelled = true }
  }, [selectedCategoryId])

  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !uploading) {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [onClose, uploading])

  const handleFilesChanged = (files: File[]) => {
    setStagedFiles(files)
    setError(null)
  }

  const effectiveDocumentType = (): string => {
    if (categories.length > 0 && selectedCategoryId) {
      return categoryFull?.category_name ?? categories.find((c) => c.id === selectedCategoryId)?.category_name ?? 'evidence'
    }
    return 'evidence'
  }

  const handleUploadDocuments = async () => {
    if (stagedFiles.length === 0) return

    setUploading(true)
    setError(null)
    const docType = effectiveDocumentType()
    const metadataJson = Object.keys(metadata).length > 0 ? JSON.stringify(metadata) : null

    try {
      const results = await Promise.allSettled(
        stagedFiles.map(async (file) => {
          const formData = new FormData()
          formData.append('file', file)
          formData.append('subject_id', subjectId)
          formData.append('document_type', docType)
          formData.append('event_id', eventId)
          if (metadataJson) formData.append('metadata', metadataJson)

          const { data, error } = await timelineApi.documents.upload(formData)
          if (error) {
            throw new Error(getApiErrorMessage(error, 'Failed to upload document'))
          }
          if (!data || typeof data !== 'object' || !('id' in data)) {
            throw new Error('Invalid response from server')
          }
          return data.id
        })
      )

      // Collect successful uploads and failed files
      const documentIds: string[] = []
      const failures: string[] = []

      results.forEach((result, idx) => {
        if (result.status === 'fulfilled') {
          documentIds.push(result.value)
        } else {
          failures.push(`${stagedFiles[idx].name}: ${result.reason.message}`)
        }
      })

      // If all failed, show error and abort
      if (documentIds.length === 0) {
        setError(`All document uploads failed:\n${failures.join('\n')}`)
        return
      }

      // If some failed, warn user but proceed with successful uploads
      if (failures.length > 0) {
        setError(`Some files failed to upload:\n${failures.join('\n')}\n\nProceeding with ${documentIds.length} successful upload(s).`)
      }

      // Create a new "document_update" event to maintain audit trail
      const eventCreateData: components['schemas']['EventCreateRequest'] = {
        subject_id: subjectId,
        event_type: 'document_update',
        schema_version: 1,
        event_time: new Date().toISOString(),
        payload: {
          original_event_id: eventId,
          original_event_type: eventType,
          document_ids: documentIds,
          action: 'documents_added'
        },
      }

      const { error: createError } = await timelineApi.events.create(eventCreateData)

      if (createError) {
        setError(getApiErrorMessage(createError, 'Failed to create document update event'))
        return
      }

      // Success - reset and notify
      setStagedFiles([])
      setShowUpload(false)
      onDocumentsUpdated?.()
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'An unexpected error occurred'
      setError(errorMsg)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose} onKeyDown={(e) => e.key === 'Escape' && !uploading && onClose()} role="presentation">
      <div
        className="bg-background border border-amber-200 dark:border-amber-900 rounded-none shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-amber-200 dark:border-amber-900 bg-linear-to-r from-amber-50 to-amber-100/50 dark:from-amber-950/30 dark:to-amber-900/20">
          <div>
            <h2 id={titleId} className="font-semibold text-foreground">Event Documents</h2>
            <p className="text-xs text-muted-foreground mt-0.5">{eventId.slice(0, 8)}</p>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            title="Close"
            aria-label="Close modal"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4 space-y-4">
          {/* Error Alert */}
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-none">
              <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
            </div>
          )}

          {/* Current Documents */}
          <div>
            <h3 className="text-sm font-medium mb-3">Current Documents</h3>
            <DocumentList eventId={eventId} readOnly />
          </div>

          {/* Upload Section */}
          {showUpload && (
            <div className="p-3 bg-linear-to-r from-blue-50 to-blue-100/50 dark:from-blue-950/30 dark:to-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-none space-y-3">
              <div>
                <h4 className="text-sm font-medium text-blue-900 dark:text-blue-200 mb-2">Add Additional Documents</h4>
                <p className="text-xs text-blue-800 dark:text-blue-300 mb-3">
                  A new "document_update" event will be created to maintain the audit trail. The original event and its documents remain unchanged.
                </p>
              </div>

              {categoriesLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                  <LoadingIcon size="sm" />
                  Loading document types…
                </div>
              ) : categories.length > 0 ? (
                <>
                  <div>
                    <label className="block text-sm font-medium text-foreground/90 mb-1">Document type</label>
                    <SingleSelectCombobox
                      value={selectedCategoryId}
                      onValueChange={setSelectedCategoryId}
                      options={categories.map((c) => ({
                        value: c.id,
                        label: c.display_name || c.category_name,
                      }))}
                      placeholder="Document type"
                      className=""
                    />
                    {categoryFull?.default_retention_days != null && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Retention: {categoryFull.default_retention_days} days
                      </p>
                    )}
                  </div>
                  {categoryFull?.metadata_schema && (
                    <div>
                      <label className="block text-sm font-medium text-foreground/90 mb-1">Metadata (optional)</label>
                      <JsonSchemaForm
                        schema={categoryFull.metadata_schema as JsonSchema}
                        value={metadata}
                        onChange={setMetadata}
                      />
                    </div>
                  )}
                </>
              ) : null}

              <EventDocumentUpload
                subjectId={subjectId}
                onFilesChanged={handleFilesChanged}
                onError={setError}
              />

              <div className="flex items-center gap-2 pt-2">
                <Button
                  onClick={handleUploadDocuments}
                  disabled={stagedFiles.length === 0 || uploading}
                  isLoading={uploading}
                  className="bg-linear-to-r from-amber-600 to-amber-700 hover:from-amber-700 hover:to-amber-800 text-white"
                >
                  {!uploading && <Plus className="w-4 h-4" />}
                  {uploading ? 'Uploading...' : 'Create Update Event'}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowUpload(false)
                    setStagedFiles([])
                    setError(null)
                  }}
                  disabled={uploading}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {/* Show Upload Button */}
          {!showUpload && (
            <Button
              variant="outline"
              onClick={() => setShowUpload(true)}
              className="w-full border-2 border-dashed border-amber-400 dark:border-amber-600 text-amber-700 dark:text-amber-300 hover:bg-amber-50 dark:hover:bg-amber-950/20 hover:border-amber-500 dark:hover:border-amber-500"
            >
              <Plus className="w-4 h-4" />
              Attach Additional Documents
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
