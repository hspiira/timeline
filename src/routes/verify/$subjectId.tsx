import { createFileRoute } from '@tanstack/react-router'
import { useState, useEffect, useCallback } from 'react'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { timelineApi } from '@/lib/api-client'
import { getApiErrorMessage } from '@/lib/api-utils'
import { CheckCircle, AlertTriangle, AlertCircle, DownloadIcon } from 'lucide-react'
import { ChainVisualization } from '@/components/verify/ChainVisualization'
import { Breadcrumbs } from '@/components/ui/Breadcrumbs'
import { SkeletonBreadcrumbs, Skeleton } from '@/components/ui/Skeleton'
import type { components } from '@/lib/timeline-api'
import { Button } from '@/components/ui/button'

export const Route = createFileRoute('/verify/$subjectId')(
  {
    component: VerifyPage,
  }
)

type ChainVerificationResponse = components['schemas']['ChainVerificationResponse']

function VerifyPage() {
  const authState = useRequireAuth()
  const { subjectId } = Route.useParams()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [verification, setVerification] = useState<ChainVerificationResponse | null>(null)

  const verifyChain = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      // Call the real verify endpoint
      const { data: verificationData, error: verifyError } = await timelineApi.events.verify(subjectId)

      if (verifyError) {
        const errorMsg = getApiErrorMessage(verifyError, 'Failed to verify chain')
        const errorStr = errorMsg.toLowerCase()

        let displayMsg = errorMsg

        // Check for specific permission/auth errors to provide contextual messages
        if (errorStr.includes('403') || errorStr.includes('forbidden') || errorStr.includes('permission') || errorStr.includes('not allowed')) {
          displayMsg = 'You do not have permission to verify this chain. Please contact your administrator if you believe this is an error.'
        } else if (errorStr.includes('401') || errorStr.includes('unauthorized')) {
          displayMsg = 'Your session has expired. Please log in again to verify the chain.'
        }

        setError(displayMsg)
      } else if (verificationData) {
        setVerification(verificationData)
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unexpected error verifying chain'
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [subjectId])

  useEffect(() => {
    if (authState.user) {
      verifyChain()
    }
  }, [authState.user, subjectId, verifyChain])

  const handleExportReport = () => {
    if (!verification) return

    const reportContent = {
      subjectId: verification.subject_id,
      tenantId: verification.tenant_id,
      verifiedAt: verification.verified_at,
      integrityStatus: verification.is_chain_valid ? 'Valid' : 'Tampered',
      summary: {
        totalEvents: verification.total_events,
        validEvents: verification.valid_events,
        invalidEvents: verification.invalid_events,
      },
      eventResults: verification.event_results?.map((e) => ({
        eventId: e.event_id,
        eventType: e.event_type,
        eventTime: e.event_time,
        sequence: e.sequence,
        isValid: e.is_valid,
        errorType: e.error_type || null,
        errorMessage: e.error_message || null,
        expectedHash: e.expected_hash || null,
        actualHash: e.actual_hash || null,
      })),
    }

    const dataStr = JSON.stringify(reportContent, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `chain-verification-${subjectId.slice(0, 8)}-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
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
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-2">
            <Skeleton className="h-7 w-1/3" />
            <Skeleton className="h-6 w-24" />
          </div>
          <div className="flex flex-wrap gap-3 mb-2">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-5 w-32" />
          </div>
          <Skeleton className="h-4 w-1/2 mb-2" />
          <Skeleton className="h-4 w-1/3" />
        </div>

        {/* Skeleton Event Chain Timeline */}
        <div className="bg-card/80 rounded-xs border border-border/50 p-3 mb-3">
          <Skeleton className="h-5 w-40 mb-2" />
          <div className="space-y-2">
            <div className="p-3 rounded-xs border border-border/50 bg-muted/30">
              <Skeleton className="h-5 w-1/2 mb-2" />
              <Skeleton className="h-4 w-1/3" />
            </div>
            <div className="p-3 rounded-xs border border-border/50 bg-muted/30">
              <Skeleton className="h-5 w-1/2 mb-2" />
              <Skeleton className="h-4 w-1/3" />
            </div>
            <div className="p-3 rounded-xs border border-border/50 bg-muted/30">
              <Skeleton className="h-5 w-1/2 mb-2" />
              <Skeleton className="h-4 w-1/3" />
            </div>
          </div>
        </div>

        {/* Skeleton Export Button */}
        <div className="flex justify-center">
          <Skeleton className="h-8 w-32" />
        </div>
      </>
    )
  }

  return (
    <>
      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[
          { label: 'Subjects', href: '/subjects' },
          { label: `${subjectId.slice(0, 8)}...`, href: `/subjects/${subjectId}` },
          { label: 'Verify' },
        ]}
      />

      {/* Error Alert */}
      {error && (
        <div className="mb-3 p-2.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xs flex gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-semibold text-red-900 dark:text-red-200 text-xs">Verification Failed</h3>
            <p className="text-xs text-red-800 dark:text-red-300 mt-0.5">{error}</p>
          </div>
          <button
            onClick={verifyChain}
            className="px-2.5 py-0.5 text-xs bg-red-600 text-white rounded hover:bg-red-700 transition-colors shrink-0"
          >
            Retry
          </button>
        </div>
      )}

      {verification && (
        <>
          {/* Header and Stats Row */}
          <div className="mb-3">
            <div className="flex items-center gap-2 mb-2">
              <h1 className="text-lg font-bold text-foreground">Chain Verification</h1>
              {verification.is_chain_valid ? (
                <div className="flex items-center gap-1 px-2.5 py-1 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xs">
                  <CheckCircle className="w-3.5 h-3.5 text-green-600 dark:text-green-400" />
                  <span className="font-semibold text-green-900 dark:text-green-200 text-xs">Valid Chain</span>
                </div>
              ) : (
                <div className="flex items-center gap-1 px-2.5 py-1 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xs">
                  <AlertTriangle className="w-3.5 h-3.5 text-red-600 dark:text-red-400" />
                  <span className="font-semibold text-red-900 dark:text-red-200 text-xs">Tampered Chain</span>
                </div>
              )}
            </div>

            {/* Compact Stats */}
            <div className="flex flex-wrap gap-3 mb-2 text-sm">
              <span className="text-muted-foreground">Total Events: <span className="font-bold text-foreground">{verification.total_events}</span></span>
              <span className="text-muted-foreground">Valid Events: <span className="font-bold text-green-600 dark:text-green-400">{verification.valid_events}</span></span>
              <span className="text-muted-foreground">Invalid Events: <span className="font-bold text-red-600 dark:text-red-400">{verification.invalid_events}</span></span>
              <span className="text-muted-foreground">Integrity: <span className={`font-bold ${verification.is_chain_valid ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>{verification.total_events > 0 ? Math.round((verification.valid_events / verification.total_events) * 100) : 0}%</span></span>
            </div>

            <p className="text-xs text-muted-foreground">Subject ID: {subjectId}</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Verified: {new Date(verification.verified_at).toLocaleString()}
            </p>
          </div>

          {/* Chain Visualization */}
          {verification.event_results && verification.event_results.length > 0 && (
            <div className="bg-card/80 rounded-xs border border-border/50 p-3 mb-3">
              <h2 className="text-sm font-semibold text-foreground mb-2">Visual Chain Overview</h2>
              <ChainVisualization
                events={verification.event_results?.map((event) => ({
                    id: event.event_id,
                    tenant_id: verification.tenant_id,
                    subject_id: verification.subject_id || subjectId,
                    event_type: event.event_type,
                    schema_version: 1,
                    event_time: event.event_time,
                    payload: {},
                    hash: event.actual_hash || event.expected_hash || '',
                    previous_hash: event.previous_hash || null,
                    created_at: event.event_time,
                    verified: event.is_valid,
                    expected_hash: event.expected_hash || '',
                    actual_hash: event.actual_hash || '',
                  })) || []}
                tamperedIndices={verification.event_results
                  ?.map((event, index) => (!event.is_valid ? index : -1))
                  .filter((i) => i !== -1) || []}
              />
            </div>
          )}

          {/* Invalid Events Summary */}
          {verification.invalid_events > 0 && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xs p-3 mb-3">
              <h2 className="text-sm font-semibold text-red-900 dark:text-red-200 mb-2">
                Chain Integrity Issues ({verification.invalid_events} {verification.invalid_events === 1 ? 'issue' : 'issues'})
              </h2>
              <p className="text-xs text-red-800 dark:text-red-300 mb-2">
                {verification.invalid_events} event{verification.invalid_events !== 1 ? 's' : ''} failed verification. See the Visual Chain Overview above for details.
              </p>
            </div>
          )}

          {/* Export Button */}
          <div className="flex justify-center">
            <Button
              onClick={handleExportReport}
              variant="primary"
              size="sm"
            >
              <DownloadIcon />
              Export Report
            </Button>
          </div>
        </>
      )}
    </>
  )
}
