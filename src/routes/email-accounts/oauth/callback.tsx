import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { CheckCircle, XCircle, Mail, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LoadingIcon } from '@/components/ui/icons'

export const Route = createFileRoute('/email-accounts/oauth/callback')({
  component: OAuthCallbackPage,
  validateSearch: (search: Record<string, unknown>) => ({
    // Success params (from backend redirect)
    success: search.success === 'true' || search.success === true,
    email_account_id: (search.email_account_id as string) || '',
    email_address: (search.email_address as string) || '',
    provider: (search.provider as string) || '',
    // Error params
    error: (search.error as string) || '',
    error_description: (search.error_description as string) || '',
    // OAuth provider params (if redirected directly here)
    code: (search.code as string) || '',
    state: (search.state as string) || '',
  }),
})

function OAuthCallbackPage() {
  const authState = useRequireAuth()
  const navigate = useNavigate()
  const searchParams = Route.useSearch()

  const [status, setStatus] = useState<'loading' | 'success' | 'error' | 'info'>('loading')
  const [errorMessage, setErrorMessage] = useState<string>('')

  useEffect(() => {
    // Check if we have OAuth provider params (code + state) - this means the redirect_uri
    // is pointing to the frontend, which is not the expected flow
    if (searchParams.code && searchParams.state) {
      setStatus('info')
      setErrorMessage(
        'OAuth callback received directly. The backend redirect_uri should point to the API callback endpoint, not the frontend. Please contact your administrator to update the OAuth configuration.'
      )
      return
    }

    // The backend callback should redirect here with query params indicating success/failure
    if (searchParams.error) {
      setStatus('error')
      setErrorMessage(searchParams.error_description || searchParams.error)
    } else if (searchParams.success || searchParams.email_account_id) {
      setStatus('success')
    } else {
      // No clear indicator - user navigated here directly
      setStatus('info')
      setErrorMessage('This page handles OAuth callbacks. Please start the connection process from the email accounts page.')
    }
  }, [searchParams])

  if (!authState.user) {
    return null
  }

  const handleViewAccount = () => {
    if (searchParams.email_account_id) {
      navigate({
        to: '/email-accounts/$accountId',
        params: { accountId: searchParams.email_account_id },
      })
    } else {
      navigate({ to: '/email-accounts' })
    }
  }

  const handleTryAgain = () => {
    navigate({ to: '/email-accounts/create' })
  }

  if (status === 'loading') {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <LoadingIcon className="w-8 h-8 mb-4" />
        <p className="text-muted-foreground">Processing OAuth callback...</p>
      </div>
    )
  }

  if (status === 'info') {
    return (
      <div className="max-w-md mx-auto">
        <div className="bg-card/80 backdrop-blur-sm border border-border/50 rounded-none p-6 text-center">
          <div className="w-12 h-12 mx-auto mb-4 rounded-none bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
            <AlertTriangle className="w-6 h-6 text-amber-600 dark:text-amber-400" />
          </div>
          <h1 className="text-lg font-bold text-foreground mb-2">OAuth Callback</h1>
          <p className="text-sm text-muted-foreground mb-6">{errorMessage}</p>
          <Button onClick={() => navigate({ to: '/email-accounts/create' })} variant="primary" size="md">
            Connect Email Account
          </Button>
        </div>
      </div>
    )
  }

  if (status === 'error') {
    const displayError =
      errorMessage || 'The OAuth authorization was not completed. This could be because you denied access or the authorization expired.'

    return (
      <div className="max-w-md mx-auto">
        <div className="bg-card/80 backdrop-blur-sm border border-border/50 rounded-none p-6 text-center">
          <div className="w-12 h-12 mx-auto mb-4 rounded-none bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
            <XCircle className="w-6 h-6 text-red-600 dark:text-red-400" />
          </div>
          <h1 className="text-lg font-bold text-foreground mb-2">Connection Failed</h1>
          <p className="text-sm text-muted-foreground mb-6">{displayError}</p>
          <div className="flex items-center justify-center gap-2">
            <Button onClick={handleTryAgain} variant="primary" size="md">
              Try Again
            </Button>
            <Button onClick={() => navigate({ to: '/email-accounts' })} variant="secondary" size="md">
              Back to Email Accounts
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // Success state
  return (
    <div className="max-w-md mx-auto">
      <div className="bg-card/80 backdrop-blur-sm border border-border/50 rounded-none p-6 text-center">
        <div className="w-12 h-12 mx-auto mb-4 rounded-none bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
          <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
        </div>
        <h1 className="text-lg font-bold text-foreground mb-2">Email Account Connected!</h1>
        <p className="text-sm text-muted-foreground mb-2">
          {searchParams.email_address ? (
            <>
              <Mail className="w-4 h-4 inline mr-1" />
              <strong>{searchParams.email_address}</strong> has been connected successfully.
            </>
          ) : (
            'Your email account has been connected successfully.'
          )}
        </p>
        {searchParams.provider && (
          <p className="text-xs text-muted-foreground mb-6 capitalize">Provider: {searchParams.provider}</p>
        )}
        <div className="flex items-center justify-center gap-2">
          <Button onClick={handleViewAccount} variant="primary" size="md">
            View Account
          </Button>
          <Button onClick={() => navigate({ to: '/email-accounts' })} variant="secondary" size="md">
            All Accounts
          </Button>
        </div>
      </div>
    </div>
  )
}
