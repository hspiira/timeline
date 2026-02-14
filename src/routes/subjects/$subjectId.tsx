import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { Calendar, Tag, AlertCircle, Boxes, FileText, Shield, ChevronLeft, ChevronRight, Upload } from 'lucide-react'
import { useEffect, useState, useCallback } from 'react'
import { useStore } from '@tanstack/react-store'
import { timelineApi } from '@/lib/api-client'
import { authStore } from '@/lib/auth-store'
import { DocumentUpload } from '@/components/documents/DocumentUpload'
import { DocumentList } from '@/components/documents/DocumentList'
import { DocumentViewer } from '@/components/documents/DocumentViewer'
import { EventBlockChain } from '@/components/events/EventBlock'
import { Breadcrumbs } from '@/components/ui/Breadcrumbs'
import { SkeletonBreadcrumbs, SkeletonEventTimeline, Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import type { SubjectResponse, EventResponse, EventListResponse } from '@/lib/types'
import { LoadingIcon } from '@/components/ui/icons'
import { Button } from '@/components/ui/button'

const PAGE_SIZE = 10

type Tab = 'events' | 'documents'

export const Route = createFileRoute('/subjects/$subjectId')({
  component: SubjectDetailPage,
  validateSearch: (search: Record<string, unknown>) => ({
    tab: (search.tab === 'documents' ? 'documents' : 'events') as Tab,
  }),
})

function SubjectDetailPage() {
  const { subjectId } = Route.useParams()
  const { tab: activeTab } = Route.useSearch({ strict: false })
  const navigate = useNavigate()
  const authState = useStore(authStore)
  const [subject, setSubject] = useState<SubjectResponse | null>(null)
  const [events, setEvents] = useState<EventResponse[]>([])
  const [totalEvents, setTotalEvents] = useState(0)
  const [currentPage, setCurrentPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [viewingDocument, setViewingDocument] = useState<{ id: string; filename: string; type: string } | null>(null)
  const [documentCounts, setDocumentCounts] = useState<Record<string, number>>({})
  const [subjectDocumentCount, setSubjectDocumentCount] = useState<number | null>(null)
  const [documentsRefreshKey, setDocumentsRefreshKey] = useState(0)
  const [showUploadPanel, setShowUploadPanel] = useState(false)

  const totalPages = Math.ceil(totalEvents / PAGE_SIZE)

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authState.isLoading && !authState.user) {
      navigate({ to: '/login', search: { tenant: '' } })
    }
  }, [authState.isLoading, authState.user, navigate])

  useEffect(() => {
    if (authState.user) {
      fetchSubject()
    }
  }, [subjectId, authState.user])

  useEffect(() => {
    setSubjectDocumentCount(null)
  }, [subjectId])

  // Fetch events when page changes
  useEffect(() => {
    if (authState.user && subject) {
      fetchEvents()
    }
  }, [currentPage, subject])

  const fetchSubjectDocumentCount = useCallback(async () => {
    const { data, error } = await timelineApi.documents.listBySubject(subjectId)
    if (!error && Array.isArray(data)) setSubjectDocumentCount(data.length)
    else setSubjectDocumentCount(0)
  }, [subjectId])

  useEffect(() => {
    if (activeTab !== 'documents' || !subjectId || !authState.user || subjectDocumentCount !== null) return
    fetchSubjectDocumentCount()
  }, [activeTab, subjectId, authState.user, subjectDocumentCount, fetchSubjectDocumentCount])

  const fetchSubject = async () => {
    setLoading(true)
    setError(null)

    try {
      // Fetch subject details
      const { data: subjectData, error: subjectError } = await timelineApi.subjects.get(
        subjectId
      )

      if (subjectError) {
        // @ts-expect-error - openapi-fetch error handling
        const errorMessage = subjectError?.message || 'Unable to load subject'
        setError(errorMessage)
        setLoading(false)
        return
      }

      if (subjectData) {
        setSubject(subjectData)
      }
    } catch (err) {
      setError('An unexpected error occurred')
      console.error('Error:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchEvents = useCallback(async () => {
    try {
      // events.list returns a flat EventListResponse[] array
      const { data: eventsList, error: eventsError } = await timelineApi.events.list(subjectId)

      if (eventsError) {
        // @ts-expect-error - openapi-fetch error handling
        const errorMessage = eventsError?.message || 'Unable to load events'
        setError(errorMessage)
      } else if (eventsList) {
        setTotalEvents(eventsList.length)

        // Paginate client-side: slice to current page
        const start = currentPage * PAGE_SIZE
        const pageItems = eventsList.slice(start, start + PAGE_SIZE)

        // Fetch full event details for the current page (needed for EventBlockChain)
        const fullEvents = await Promise.all(
          pageItems.map(async (item: EventListResponse) => {
            const { data } = await timelineApi.events.get(item.id)
            return data
          })
        )
        setEvents(fullEvents.filter((e): e is EventResponse => e != null))

        // Load document counts for page events
        const documentPromises = pageItems.map(async (item: EventListResponse) => {
          try {
            const { data: docs, error } = await timelineApi.documents.listByEvent(item.id)
            if (error) {
              return { eventId: item.id, count: 0 }
            }
            return { eventId: item.id, count: Array.isArray(docs) ? docs.length : 0 }
          } catch {
            return { eventId: item.id, count: 0 }
          }
        })

        const documentResults = await Promise.all(documentPromises)
        const counts: Record<string, number> = {}
        documentResults.forEach(({ eventId, count }: { eventId: string; count: number }) => {
          counts[eventId] = count
        })
        setDocumentCounts(counts)
      }
    } catch (err) {
      setError('An unexpected error occurred')
      console.error('Error:', err)
    }
  }, [subjectId, currentPage])

  const goToPage = (page: number) => {
    if (page >= 0 && page < totalPages) {
      setCurrentPage(page)
    }
  }

  if (authState.isLoading) {
    return (
      <div className="min-h-[calc(100vh-4rem)] bg-background flex items-center justify-center">
        <div className="flex items-center gap-3 text-muted-foreground">
          <LoadingIcon />
        </div>
      </div>
    )
  }

  if (!authState.user) {
    return null
  }

  if (loading) {
    return (
      <>
        {/* Skeleton Breadcrumbs */}
        <SkeletonBreadcrumbs />

        {/* Skeleton Header */}
        <div className="bg-card/80 backdrop-blur-sm rounded-none p-4 border border-border/50 mb-4">
          <div className="flex items-start justify-between mb-3">
            <div className="flex-1">
              <Skeleton className="h-8 w-1/2 mb-2" />
              <div className="flex items-center gap-3">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-32" />
              </div>
            </div>
            <Skeleton className="h-8 w-20" />
          </div>
          <Skeleton className="h-10 w-32 mt-2" />
        </div>

        {/* Skeleton Tabs */}
        <div className="flex gap-1 mb-3 border-b border-border">
          <Skeleton className="h-8 w-20" />
          <Skeleton className="h-8 w-24" />
        </div>

        {/* Skeleton Timeline */}
        <div className="bg-card/80 backdrop-blur-sm rounded-none p-4 border border-border/50">
          <Skeleton className="h-5 w-32 mb-4" />
          <SkeletonEventTimeline />
        </div>
      </>
    )
  }

  if (error || !subject) {
    return (
      <div className="min-h-[calc(100vh-4rem)] bg-background flex items-center justify-center">
        <div className="text-center max-w-md px-4">
          <div className="w-16 h-16 rounded-none bg-red-100 dark:bg-red-900/20 flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">
            Unable to Load Subject
          </h3>
          <p className="text-muted-foreground mb-6">
            {error || 'Subject not found'}. Please check your connection and try again.
          </p>
          <div className="flex items-center justify-center gap-3">
            <Button
              onClick={fetchSubject}
              variant="primary"
              size="sm"
            >
              <LoadingIcon />
              Retry
            </Button>
            <Button
              onClick={() => navigate({ to: '/subjects' })}
              variant="ghost"
              size="sm"
            >
              Back to Subjects
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Document Viewer Modal */}
      {viewingDocument && (
        <DocumentViewer
          documentId={viewingDocument.id}
          filename={viewingDocument.filename}
          fileType={viewingDocument.type}
          onClose={() => setViewingDocument(null)}
        />
      )}

      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[
          { label: 'Subjects', href: '/subjects' },
          { label: subject.id },
        ]}
      />

      {/* Subject Header */}
      <div className="bg-card/80 backdrop-blur-sm rounded-none p-4 border border-border/50 mb-4">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h1 className="text-2xl font-bold text-foreground mb-1">
              {subject.id}
            </h1>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                <Tag className="w-3 h-3" />
                <span className="font-medium">{subject.subject_type}</span>
              </div>
              {subject.external_ref && (
                <div className="flex items-center gap-1">
                  <span>Ref:</span>
                  <span className="font-mono">{subject.external_ref}</span>
                </div>
              )}
              <div className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                <span>{totalEvents} event{totalEvents !== 1 ? 's' : ''}</span>
              </div>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Total Blocks</p>
            <p className="text-2xl font-bold text-foreground">
              {totalEvents}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2 border-t border-border">
          <Button
            onClick={() => navigate({ to: `/verify/${subjectId}` })}
            variant="primary"
            size="sm"
          >
            <Shield className="w-4 h-4" />
            Verify Chain
          </Button>
        </div>
      </div>

      {/* Tabs — persisted in URL so reload keeps tab */}
      <div className="flex gap-1 mb-3 border-b border-border">
        <button
          onClick={() => navigate({ to: '/subjects/$subjectId', params: { subjectId }, search: { tab: 'events' } })}
          className={`px-3 py-2 text-xs font-medium transition-colors border-b-2 rounded-none flex items-center gap-2 ${
            activeTab === 'events'
              ? 'bg-muted/40 border-primary text-foreground'
              : 'bg-transparent border-transparent text-foreground/60 hover:bg-muted/20'
          }`}
        >
          <Boxes className="w-4 h-4" />
          Event Chain
        </button>
        <button
          onClick={() => navigate({ to: '/subjects/$subjectId', params: { subjectId }, search: { tab: 'documents' } })}
          className={`px-3 py-2 text-xs font-medium transition-colors border-b-2 rounded-none flex items-center gap-2 ${
            activeTab === 'documents'
              ? 'bg-muted/40 border-primary text-foreground'
              : 'bg-transparent border-transparent text-foreground/60 hover:bg-muted/20'
          }`}
        >
          <FileText className="w-4 h-4" />
          Documents
        </button>
      </div>

      {/* Content */}
      {activeTab === 'events' && (
        <div>
          {events.length === 0 ? (
            <div className="bg-card/80 backdrop-blur-sm rounded-none p-4 border border-border/50">
              <EmptyState
                icon={Boxes}
                title="No events recorded"
                description="Events for this subject will appear here once created"
                action={{
                  label: 'Record First Event',
                  onClick: () => navigate({ to: '/events/create' }),
                }}
              />
            </div>
          ) : (
            <>
              <EventBlockChain
                events={events}
                documentCounts={documentCounts}
                totalEvents={totalEvents}
                pageOffset={currentPage * PAGE_SIZE}
              />

              {/* Pagination Controls */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 px-4 py-3 bg-card/80 backdrop-blur-sm rounded-none border border-border/50">
                  <div className="text-xs text-muted-foreground">
                    Showing {currentPage * PAGE_SIZE + 1} - {Math.min((currentPage + 1) * PAGE_SIZE, totalEvents)} of {totalEvents} events
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      onClick={() => goToPage(currentPage - 1)}
                      disabled={currentPage === 0}
                      variant="ghost"
                      size="sm"
                    >
                      <ChevronLeft className="w-4 h-4" />
                      Previous
                    </Button>
                    <span className="text-xs text-muted-foreground px-2">
                      Page {currentPage + 1} of {totalPages}
                    </span>
                    <Button
                      onClick={() => goToPage(currentPage + 1)}
                      disabled={currentPage >= totalPages - 1}
                      variant="ghost"
                      size="sm"
                    >
                      Next
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Documents Tab — only upload when no docs (no library section); library + Upload button when has docs */}
      {activeTab === 'documents' && (
        <div className="relative overflow-hidden rounded-none animate-in fade-in duration-300">
          <div
            className="absolute inset-0 -z-[1] opacity-[0.4] dark:opacity-[0.08]"
            style={{
              backgroundImage: `radial-gradient(ellipse 80% 50% at 50% -20%, oklch(0.4 0.02 260 / 0.12), transparent),
                radial-gradient(ellipse 60% 40% at 100% 100%, oklch(0.35 0.02 260 / 0.08), transparent)`,
            }}
          />
          <div className="relative space-y-6 p-1">
            {(subjectDocumentCount === null || subjectDocumentCount === 0) && (
              <section
                className="rounded-none border border-border/60 bg-card/90 backdrop-blur-sm shadow-sm overflow-hidden animate-in fade-in slide-in-from-top-1 duration-250"
                style={{ animationDelay: '0ms', animationFillMode: 'backwards' }}
              >
                <div className="border-l-[3px] border-primary bg-muted/20 dark:bg-muted/10 px-4 py-3 flex items-center gap-2">
                  <Upload className="w-4 h-4 text-primary shrink-0" aria-hidden />
                  <span className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                    Add documents
                  </span>
                </div>
                <div className="p-4 sm:p-5 space-y-4">
                  <DocumentUpload
                    subjectId={subjectId}
                    onError={(err) => console.error('Upload error:', err)}
                    onUploadComplete={() => {
                      fetchSubjectDocumentCount()
                    }}
                  />
                  <p className="text-sm text-muted-foreground text-center">
                    No documents yet. Upload files above.
                  </p>
                </div>
              </section>
            )}

            {(subjectDocumentCount ?? 0) > 0 && (
              <section
                className="rounded-none border border-border/60 bg-card/90 backdrop-blur-sm shadow-sm overflow-hidden animate-in fade-in slide-in-from-bottom-1 duration-250"
                style={{ animationDelay: '0ms', animationFillMode: 'backwards' }}
              >
                <div className="border-l-[3px] border-border bg-muted/15 dark:bg-muted/10 px-4 py-3 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-muted-foreground shrink-0" aria-hidden />
                    <span className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                      Document library
                    </span>
                  </div>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => setShowUploadPanel((v) => !v)}
                    className="shrink-0"
                  >
                    <Upload className="w-3.5 h-3.5" />
                    {showUploadPanel ? 'Hide upload' : 'Upload'}
                  </Button>
                </div>
                {showUploadPanel && (
                  <div className="border-t border-border/60 bg-muted/10 px-4 py-4">
                    <DocumentUpload
                      subjectId={subjectId}
                      onError={(err) => console.error('Upload error:', err)}
                      onUploadComplete={() => {
                        setDocumentsRefreshKey((k) => k + 1)
                        setShowUploadPanel(false)
                      }}
                    />
                  </div>
                )}
                <div className="p-4 sm:p-5">
                  <DocumentList
                    key={documentsRefreshKey}
                    subjectId={subjectId}
                    onError={(err) => console.error('Documents error:', err)}
                    onDocumentsLoaded={setSubjectDocumentCount}
                  />
                </div>
              </section>
            )}
          </div>
        </div>
      )}
    </>
  )
}
