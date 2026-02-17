import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { Calendar, Tag, AlertCircle, Activity, FileText, Shield, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'
import { useEffect, useState, useCallback } from 'react'
import { useStore } from '@tanstack/react-store'
import { timelineApi } from '@/lib/api-client'
import { authStore } from '@/lib/auth-store'
import { DocumentUpload } from '@/components/documents/DocumentUpload'
import { DocumentList } from '@/components/documents/DocumentList'
import { DocumentViewer } from '@/components/documents/DocumentViewer'
import { EventsTable } from '@/components/events/EventsTable'
import { EventDetailsModal } from '@/components/events/EventDetailsModal'
import { EventDocumentsModal } from '@/components/documents/EventDocumentsModal'
import { Breadcrumbs } from '@/components/ui/Breadcrumbs'
import { SkeletonBreadcrumbs, SkeletonEventTimeline, Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import type { SubjectResponse, EventResponse, EventListResponse } from '@/lib/types'
import { LoadingIcon } from '@/components/ui/icons'
import { Button } from '@/components/ui/button'

const PAGE_SIZE = 50

export const Route = createFileRoute('/events/subject/$subjectId')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  component: SubjectEventsPage,
})

type Tab = 'events' | 'documents'

function SubjectEventsPage() {
  const { subjectId } = Route.useParams()
  const navigate = useNavigate()
  const authState = useStore(authStore)
  const [subject, setSubject] = useState<SubjectResponse | null>(null)
  const [events, setEvents] = useState<EventResponse[]>([])
  const [totalEvents, setTotalEvents] = useState(0)
  const [currentPage, setCurrentPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('events')
  const [viewingDocument, setViewingDocument] = useState<{ id: string; filename: string; type: string } | null>(null)
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const [detailsEventId, setDetailsEventId] = useState<string | null>(null)
  const [documentCounts, setDocumentCounts] = useState<Record<string, number>>({})

  const totalPages = Math.ceil(totalEvents / PAGE_SIZE)

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authState.isLoading && !authState.user) {
      navigate({ to: '/login', search: { tenant: '' } })
    }
  }, [authState.isLoading, authState.user, navigate])

  const goToPage = (page: number) => {
    if (page >= 0 && page < totalPages) {
      setCurrentPage(page)
    }
  }

  const fetchEvents = useCallback(async (page: number) => {
    setLoading(true)
    try {
      // events.list returns a flat EventListResponse[] array
      const { data: eventsList, error: eventsError } = await timelineApi.events.list(subjectId)

      if (eventsError) {
        // @ts-expect-error - openapi-fetch error handling
        const errorMessage = eventsError?.message || 'Unable to load events'
        setError(errorMessage)
      } else if (eventsList) {
        setTotalEvents(eventsList.length)

        // Paginate client-side
        const start = page * PAGE_SIZE
        const pageItems = eventsList.slice(start, start + PAGE_SIZE)

        // Fetch full event details for the current page (needed for EventCard)
        const fullEvents = await Promise.all(
          pageItems.map(async (item: EventListResponse) => {
            const { data } = await timelineApi.events.get(item.id)
            return data
          })
        )
        setEvents(fullEvents.filter((e): e is EventResponse => e != null))

        // Load document counts for current page events
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
    } finally {
      setLoading(false)
    }
  }, [subjectId])

  useEffect(() => {
    if (authState.user) {
      fetchData()
    }
  }, [subjectId, authState.user])

  useEffect(() => {
    if (authState.user && subject) {
      fetchEvents(currentPage)
    }
  }, [currentPage, authState.user, subject, fetchEvents])

  const fetchData = async () => {
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

      // Events will be fetched by the useEffect that watches currentPage
    } catch (err) {
      setError('An unexpected error occurred')
      console.error('Error:', err)
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
              onClick={fetchData}
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
              <p className="text-xs text-muted-foreground">Total Events</p>
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

        {/* Tabs */}
        <div className="flex gap-1 mb-3 border-b border-border">
          <Button
            onClick={() => setActiveTab('events')}
            className={`px-3 py-2 text-xs font-medium transition-colors border-b-2 ${
              activeTab === 'events'
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            <span className="flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Events
            </span>
          </Button>
          <Button
            onClick={() => setActiveTab('documents')}
            className={`px-3 py-2 text-xs font-medium transition-colors border-b-2 ${
              activeTab === 'documents'
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            <span className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Documents
            </span>
          </Button>
        </div>

        {/* Content */}
        {activeTab === 'events' && (
        <div className="bg-card/80 backdrop-blur-sm rounded-none p-4 border border-border/50">
          <h2 className="text-sm font-semibold text-foreground mb-4">
            Event Timeline
          </h2>

          {events.length === 0 ? (
            <EmptyState
              icon={Calendar}
              title="No events recorded"
              description="Events for this subject will appear here once they are created"
              action={{
                label: 'Record First Event',
                onClick: () => navigate({ to: '/events/create' }),
              }}
            />
          ) : (
            <EventsTable
              events={events}
              documentCounts={documentCounts}
              showSubjectColumn={false}
              onViewDetails={(e) => setDetailsEventId(e.id)}
              onViewDocuments={(e) => setSelectedEventId(e.id)}
            />
          )}

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-6 pt-4 border-t border-border">
              <div className="text-xs text-muted-foreground">
                Showing {currentPage * PAGE_SIZE + 1}-{Math.min((currentPage + 1) * PAGE_SIZE, totalEvents)} of {totalEvents} events
              </div>
              <div className="flex items-center gap-1">
                <Button
                  onClick={() => goToPage(0)}
                  disabled={currentPage === 0}
                  variant="ghost"
                  size="sm"
                  title="First page"
                >
                  <ChevronsLeft className="w-4 h-4" />
                </Button>
                <Button
                  onClick={() => goToPage(currentPage - 1)}
                  disabled={currentPage === 0}
                  variant="ghost"
                  size="sm"
                  title="Previous page"
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="px-3 text-xs text-foreground">
                  Page {currentPage + 1} of {totalPages}
                </span>
                <Button
                  onClick={() => goToPage(currentPage + 1)}
                  disabled={currentPage >= totalPages - 1}
                  variant="ghost"
                  size="sm"
                  title="Next page"
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
                <Button
                  onClick={() => goToPage(totalPages - 1)}
                  disabled={currentPage >= totalPages - 1}
                  variant="ghost"
                  size="sm"
                  title="Last page"
                >
                  <ChevronsRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </div>
        )}

        {/* Documents Tab */}
        {activeTab === 'documents' && (
        <div className="space-y-4">
          {/* Documents List */}
          <div className="bg-card/80 backdrop-blur-sm rounded-none p-4 border border-border/50">
            <h2 className="text-sm font-semibold text-foreground mb-4">Documents</h2>
            <DocumentList
              subjectId={subjectId}
              onError={(error) => console.error('Documents error:', error)}
            />
          </div>

          {/* Upload Section */}
          <div className="bg-card/80 backdrop-blur-sm rounded-none p-4 border border-border/50">
            <h2 className="text-sm font-semibold text-foreground mb-4">Upload New Document</h2>
            <DocumentUpload
              subjectId={subjectId}
              onError={(error) => console.error('Upload error:', error)}
            />
          </div>
        </div>
        )}

        {/* Event Details Modal */}
        {detailsEventId && events.length > 0 && (() => {
          const event = events.find(e => e.id === detailsEventId)
          return event ? (
            <EventDetailsModal
              event={event}
              onClose={() => setDetailsEventId(null)}
            />
          ) : null
        })()}

        {/* Event Documents Modal */}
        {selectedEventId && events.length > 0 && (() => {
          const event = events.find(e => e.id === selectedEventId)
          return event ? (
            <EventDocumentsModal
              eventId={event.id}
              subjectId={event.subject_id}
              eventType={event.event_type}
              onClose={() => setSelectedEventId(null)}
              onDocumentsUpdated={() => {
                setSelectedEventId(null)
                fetchData()
              }}
            />
          ) : null
        })()}
    </>
  )
}
