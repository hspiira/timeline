import { createFileRoute, useNavigate, Link } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import {
  ArrowLeft,
  Calendar,
  Hash,
  Link2,
  FileText,
  CheckCircle,
  Clock,
  Copy,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
} from 'lucide-react'
import { timelineApi } from '@/lib/api-client'
import { formatFullDateTime } from '@/lib/format-date'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { Breadcrumbs } from '@/components/ui/Breadcrumbs'
import { SkeletonBreadcrumbs, Skeleton } from '@/components/ui/Skeleton'
import { Button } from '@/components/ui/button'
import { DocumentList } from '@/components/documents/DocumentList'
import { LoadingIcon } from '@/components/ui/icons'
import type { EventResponse, EventListResponse } from '@/lib/types'

export const Route = createFileRoute('/subjects/$subjectId_/events/$eventId')({
  component: EventDetailPage,
})

function EventDetailPage() {
  const { subjectId, eventId } = Route.useParams()
  const navigate = useNavigate()
  const authState = useRequireAuth()

  const [event, setEvent] = useState<EventResponse | null>(null)
  const [allEvents, setAllEvents] = useState<EventListResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copiedField, setCopiedField] = useState<string | null>(null)

  useEffect(() => {
    if (authState.user) {
      fetchData()
    }
  }, [eventId, subjectId, authState.user])

  const fetchData = async () => {
    setLoading(true)
    setError(null)

    try {
      // Fetch the specific event
      const { data: eventData, error: eventError } = await timelineApi.events.get(eventId)

      if (eventError) {
        setError('Unable to load event')
        setLoading(false)
        return
      }

      if (eventData) {
        setEvent(eventData)
      }

      // Fetch all events for navigation — events.list returns flat EventListResponse[]
      const { data: eventsData } = await timelineApi.events.list(subjectId)
      if (eventsData) {
        // Sort by event_time ascending
        const sorted = [...eventsData].sort(
          (a, b) => new Date(a.event_time).getTime() - new Date(b.event_time).getTime()
        )
        setAllEvents(sorted)
      }
    } catch (err) {
      setError('An unexpected error occurred')
      console.error('Error:', err)
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text)
    setCopiedField(field)
    setTimeout(() => setCopiedField(null), 2000)
  }

  // Find current event index and neighbors
  const currentIndex = allEvents.findIndex((e) => e.id === eventId)
  const prevEvent = currentIndex > 0 ? allEvents[currentIndex - 1] : null
  const nextEvent = currentIndex < allEvents.length - 1 ? allEvents[currentIndex + 1] : null
  const isGenesis = currentIndex === 0

  if (authState.isLoading) {
    return (
      <div className="min-h-[calc(100vh-4rem)] bg-background flex items-center justify-center">
        <LoadingIcon />
      </div>
    )
  }

  if (!authState.user) {
    return null
  }

  if (loading) {
    return (
      <>
        <SkeletonBreadcrumbs />
        <div className="space-y-4">
          <Skeleton className="h-8 w-1/3" />
          <div className="bg-card rounded-none border p-4 space-y-3">
            <Skeleton className="h-6 w-1/2" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-32 w-full" />
          </div>
        </div>
      </>
    )
  }

  if (error || !event) {
    return (
      <div className="min-h-[calc(100vh-4rem)] bg-background flex items-center justify-center">
        <div className="text-center max-w-md px-4">
          <div className="w-16 h-16 rounded-none bg-red-100 dark:bg-red-900/20 flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">Unable to Load Event</h3>
          <p className="text-muted-foreground mb-6">{error || 'Event not found'}</p>
          <div className="flex items-center justify-center gap-3">
            <Button onClick={fetchData} variant="primary" size="sm">
              <LoadingIcon />
              Retry
            </Button>
            <Button
              onClick={() => navigate({ to: `/subjects/${subjectId}` })}
              variant="ghost"
              size="sm"
            >
              Back to Subject
            </Button>
          </div>
        </div>
      </div>
    )
  }

  const HashField = ({
    label,
    value,
    fieldKey,
  }: {
    label: string
    value: string | null
    fieldKey: string
  }) => {
    if (!value) return null
    const isCopied = copiedField === fieldKey

    return (
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground">{label}</label>
        <div className="flex items-center gap-2 group">
          <code className="flex-1 font-mono text-xs bg-muted/50 px-3 py-2 rounded-none break-all">
            {value}
          </code>
          <button
            onClick={() => copyToClipboard(value, fieldKey)}
            className="p-2 hover:bg-muted rounded-none transition-colors opacity-0 group-hover:opacity-100"
            title="Copy"
          >
            {isCopied ? (
              <CheckCircle className="w-4 h-4 text-green-500" />
            ) : (
              <Copy className="w-4 h-4 text-muted-foreground" />
            )}
          </button>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[
          { label: 'Subjects', href: '/subjects' },
          { label: subjectId.slice(0, 8) + '...', href: `/subjects/${subjectId}` },
          { label: `Event #${currentIndex.toString().padStart(3, '0')}` },
        ]}
      />

      {/* Navigation Header */}
      <div className="flex items-center justify-between mb-4">
        <Button
          onClick={() => navigate({ to: `/subjects/${subjectId}` })}
          variant="ghost"
          size="sm"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Chain
        </Button>

        <div className="flex items-center gap-2">
          {prevEvent ? (
            <Link
              to="/subjects/$subjectId/events/$eventId"
              params={{ subjectId, eventId: prevEvent.id }}
              className="p-2 hover:bg-muted rounded-none transition-colors"
              title="Previous event"
            >
              <ChevronLeft className="w-4 h-4" />
            </Link>
          ) : (
            <div className="p-2 text-muted-foreground/30">
              <ChevronLeft className="w-4 h-4" />
            </div>
          )}

          <span className="text-sm text-muted-foreground">
            {currentIndex + 1} of {allEvents.length}
          </span>

          {nextEvent ? (
            <Link
              to="/subjects/$subjectId/events/$eventId"
              params={{ subjectId, eventId: nextEvent.id }}
              className="p-2 hover:bg-muted rounded-none transition-colors"
              title="Next event"
            >
              <ChevronRight className="w-4 h-4" />
            </Link>
          ) : (
            <div className="p-2 text-muted-foreground/30">
              <ChevronRight className="w-4 h-4" />
            </div>
          )}
        </div>
      </div>

      {/* Event Block Header */}
      <div className="bg-card rounded-none border border-border overflow-hidden mb-4">
        <div className="px-4 py-3 border-b border-border bg-muted/30">
          <div className="flex items-center gap-3">
            {isGenesis ? (
              <div className="w-10 h-10 rounded-none bg-primary/20 border-2 border-primary flex items-center justify-center">
                <span className="text-sm font-bold text-primary">G</span>
              </div>
            ) : (
              <div className="w-10 h-10 rounded-none bg-muted border-2 border-border flex items-center justify-center">
                <span className="text-sm font-semibold text-muted-foreground">
                  {currentIndex.toString().padStart(2, '0')}
                </span>
              </div>
            )}

            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-foreground">{event.event_type}</h1>
                {isGenesis && (
                  <span className="px-2 py-0.5 text-xs font-medium bg-primary/10 text-primary rounded-none">
                    Genesis Block
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                <span className="font-mono">{event.id.slice(0, 12)}...</span>
                <span>v{event.schema_version}</span>
              </div>
            </div>

            <CheckCircle className="w-6 h-6 text-green-500" />
          </div>
        </div>

        {/* Event Metadata */}
        <div className="p-4 space-y-4">
          {/* Time & Subject */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center gap-3 p-3 bg-muted/30 rounded-none">
              <Clock className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Event Time</p>
                <p className="text-sm font-medium">
                  {formatFullDateTime(event.event_time)}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 p-3 bg-muted/30 rounded-none">
              <Calendar className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Schema Version</p>
                <p className="text-sm font-medium">v{event.schema_version}</p>
              </div>
            </div>
          </div>

          {/* Hashes */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <Hash className="w-4 h-4" />
              Cryptographic Hashes
            </h3>

            <HashField label="Event Hash" value={event.hash} fieldKey="hash" />

            {isGenesis ? (
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Previous Hash</label>
                <div className="px-3 py-2 bg-primary/5 border border-primary/20 rounded-none text-xs text-primary">
                  Genesis block - no previous hash
                </div>
              </div>
            ) : (
              <HashField label="Previous Hash" value={(event.payload as any)?.previous_hash ?? null} fieldKey="prev_hash" />
            )}

            {/* Chain Link Visualization */}
            {prevEvent && (
              <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-800 rounded-none">
                <Link2 className="w-4 h-4 text-green-600" />
                <span className="text-xs text-green-700 dark:text-green-300">
                  Chain link verified: This event's previous_hash matches block #{currentIndex - 1}'s
                  hash
                </span>
              </div>
            )}
          </div>

          {/* Payload */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold">Event Payload</h3>
            <div className="bg-slate-50 dark:bg-slate-900/50 rounded-none border border-slate-200 dark:border-slate-700 overflow-hidden">
              <pre className="p-4 text-xs font-mono text-foreground overflow-x-auto max-h-96">
                {JSON.stringify(event.payload, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      </div>

      {/* Documents Section */}
      <div className="bg-card rounded-none border border-border overflow-hidden">
        <div className="px-4 py-3 border-b border-border bg-muted/30">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Attached Documents
          </h2>
        </div>
        <div className="p-4">
          <DocumentList eventId={eventId} onError={(err) => console.error('Documents error:', err)} />
        </div>
      </div>
    </>
  )
}
