import { createFileRoute } from '@tanstack/react-router'
import { useState, useCallback } from 'react'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { timelineApi } from '@/lib/api-client'
import { getApiErrorDisplay } from '@/lib/api-utils'
import { CheckCircle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ErrorAlert } from '@/components/ui/ErrorAlert'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/verify/tenant')({
  component: VerifyTenantPage,
})

type ChainVerificationResponse = components['schemas']['ChainVerificationResponse']
type VerificationJobStatusResponse = components['schemas']['VerificationJobStatusResponse']

const POLL_INTERVAL_MS = 2000

function VerifyTenantPage() {
  const authState = useRequireAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [status, setStatus] = useState<VerificationJobStatusResponse | null>(null)

  const runVerification = useCallback(async () => {
    setLoading(true)
    setError(null)
    setJobId(null)
    setStatus(null)

    try {
      const startRes = await timelineApi.events.startVerificationJob()
      const res = startRes as { data?: { job_id: string }; error?: unknown; response?: { status?: number } }
      if (res.error || !res.data) {
        const display = getApiErrorDisplay(
          { error: res.error, status: res.response?.status },
          'Failed to start verification'
        )
        setError(display.message)
        setLoading(false)
        return
      }

      const id = res.data.job_id
      setJobId(id)

      const poll = async (): Promise<ChainVerificationResponse | null> => {
        const jobRes = await timelineApi.events.getVerificationJobStatus(id)
        if (jobRes.error || !jobRes.data) {
          setError('Failed to get job status')
          return null
        }
        setStatus(jobRes.data)
        if (jobRes.data.status === 'completed' && jobRes.data.result) {
          return jobRes.data.result
        }
        if (jobRes.data.status === 'failed') {
          setError(jobRes.data.error ?? 'Verification failed')
          return null
        }
        await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS))
        return poll()
      }

      await poll()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error')
    } finally {
      setLoading(false)
    }
  }, [])

  if (!authState.user) return null

  const result = status?.status === 'completed' ? status.result : null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Verify all chains</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Run verification for all event chains in your tenant. For large tenants this runs in the background.
        </p>
      </div>

      {error && <ErrorAlert message={error} />}

      {!result && !loading && (
        <Button onClick={runVerification} disabled={loading}>
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
              Verifying…
            </>
          ) : (
            'Verify all chains'
          )}
        </Button>
      )}

      {loading && jobId && (
        <p className="text-sm text-muted-foreground">
          Job {jobId.slice(0, 8)}… {status?.status === 'running' ? 'Running…' : status?.status ?? 'Pending…'}
        </p>
      )}

      {result && (
        <div className="rounded-xs border bg-card p-4 space-y-2">
          <div className="flex items-center gap-2 text-foreground font-medium">
            <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
            Verification complete
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <span className="text-muted-foreground">Total events:</span>
            <span className="font-medium">{result.total_events}</span>
            <span className="text-muted-foreground">Valid:</span>
            <span className="font-medium text-green-600 dark:text-green-400">{result.valid_events}</span>
            <span className="text-muted-foreground">Invalid:</span>
            <span className="font-medium text-destructive">{result.invalid_events}</span>
            <span className="text-muted-foreground">Chain valid:</span>
            <span className={result.is_chain_valid ? 'text-green-600 dark:text-green-400' : 'text-destructive'}>
              {result.is_chain_valid ? 'Yes' : 'No'}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
