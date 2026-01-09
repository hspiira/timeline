import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { Calendar, Tag, AlertCircle, Boxes, FileText, Shield } from 'lucide-react'
import { useEffect, useState } from 'react'
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
import type { SubjectResponse, EventResponse } from '@/lib/types'
import { LoadingIcon } from '@/components/ui/icons'
import { Button } from '@/components/ui/button'

export const Route = createFileRoute('/subjects/$subjectId')({
  component: SubjectDetailPage,
})

type Tab = 'events' | 'documents'

function SubjectDetailPage() {
  const { subjectId } = Route.useParams()
  const navigate = useNavigate()
  const authState = useStore(authStore)
  const [subject, setSubject] = useState<SubjectResponse | null>(null)
  const [events, setEvents] = useState<EventResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('events')
  const [viewingDocument, setViewingDocument] = useState<{ id: string; filename: string; type: string } | null>(null)
  const [documentCounts, setDocumentCounts] = useState<Record<string, number>>({})

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authState.isLoading && !authState.user) {
      navigate({ to: '/login' })
    }
  }, [authState.isLoading, authState.user, navigate])

  useEffect(() => {
    if (authState.user) {
      fetchData()
    }
  }, [subjectId, authState.user])

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

      // Fetch events for subject
      const { data: eventsData, error: eventsError } = await timelineApi.events.list(
        subjectId
      )

      if (eventsError) {
        // @ts-expect-error - openapi-fetch error handling
        const errorMessage = eventsError?.message || 'Unable to load events'
        setError(errorMessage)
      } else if (eventsData) {
        setEvents(eventsData)

        // Load document counts for all events
        const documentPromises = eventsData.map(async (event) => {
          try {
            const { data: docs, error } = await timelineApi.documents.listByEvent(event.id)
            if (error) {
              return { eventId: event.id, count: 0 }
            }
            return { eventId: event.id, count: Array.isArray(docs) ? docs.length : 0 }
          } catch (err) {
            return { eventId: event.id, count: 0 }
          }
        })

        const documentResults = await Promise.all(documentPromises)
        const counts: Record<string, number> = {}
        documentResults.forEach(({ eventId, count }) => {
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
        <div className="bg-card/80 backdrop-blur-sm rounded-xs p-4 border border-border/50 mb-4">
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
        <div className="bg-card/80 backdrop-blur-sm rounded-xs p-4 border border-border/50">
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
          <div className="w-16 h-16 rounded-xs bg-red-100 dark:bg-red-900/20 flex items-center justify-center mx-auto mb-4">
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
      <div className="bg-card/80 backdrop-blur-sm rounded-xs p-4 border border-border/50 mb-4">
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
                <span>Created {new Date(subject.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Total Blocks</p>
            <p className="text-2xl font-bold text-foreground">
              {events.length}
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
        <button
          onClick={() => setActiveTab('events')}
          className={`px-3 py-2 text-xs font-medium transition-colors border-b-2 rounded-t-xs flex items-center gap-2 ${
            activeTab === 'events'
              ? 'bg-muted/40 border-primary text-foreground'
              : 'bg-transparent border-transparent text-foreground/60 hover:bg-muted/20'
          }`}
        >
          <Boxes className="w-4 h-4" />
          Event Chain
        </button>
        <button
          onClick={() => setActiveTab('documents')}
          className={`px-3 py-2 text-xs font-medium transition-colors border-b-2 rounded-t-xs flex items-center gap-2 ${
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
            <div className="bg-card/80 backdrop-blur-sm rounded-xs p-4 border border-border/50">
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
            <EventBlockChain events={events} documentCounts={documentCounts} />
          )}
        </div>
      )}

      {/* Documents Tab */}
      {activeTab === 'documents' && (
        <div className="space-y-4">
          {/* Documents List */}
          <div className="bg-card/80 backdrop-blur-sm rounded-xs p-4 border border-border/50">
            <h2 className="text-sm font-semibold text-foreground mb-4">Documents</h2>
            <DocumentList
              subjectId={subjectId}
              onError={(err) => console.error('Documents error:', err)}
            />
          </div>

          {/* Upload Section */}
          <div className="bg-card/80 backdrop-blur-sm rounded-xs p-4 border border-border/50">
            <h2 className="text-sm font-semibold text-foreground mb-4">Upload New Document</h2>
            <DocumentUpload
              subjectId={subjectId}
              onError={(err) => console.error('Upload error:', err)}
            />
          </div>
        </div>
      )}
    </>
  )
}
