import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useStore } from '@tanstack/react-store'
import { ArrowLeft, CheckCircle, Copy, KeyRound } from 'lucide-react'
import { useState } from 'react'
import { AuthCard } from '@/components/auth/AuthCard'
import { AuthPageLayout } from '@/components/auth/AuthPageLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { authActions, authStore } from '@/lib/auth-store'
import { formatFullDateTime } from '@/lib/format-date'
import { useRedirectIfAuthenticated } from '@/lib/hooks'

export const Route = createFileRoute('/register')({
  component: RegisterTenantPage,
})

/** C2 tenant creation response: admin sets password via set_password_url. */
interface TenantCreationResult {
  tenant_id: string
  tenant_code: string
  tenant_name: string
  admin_username: string
  admin_email: string
  set_password_url?: string | null
  set_password_expires_at?: string | null
}

function RegisterTenantPage() {
  const navigate = useNavigate()
  const authState = useStore(authStore)
  const [tenantCode, setTenantCode] = useState('')
  const [tenantName, setTenantName] = useState('')
  const [createdTenant, setCreatedTenant] = useState<TenantCreationResult | null>(null)
  const [copied, setCopied] = useState(false)

  const isAuthenticated = useRedirectIfAuthenticated()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    authActions.clearError()
    try {
      const result = await authActions.registerTenant({
        code: tenantCode.trim(),
        name: tenantName.trim(),
      })
      setCreatedTenant(result)
    } catch (error) {
      console.error('Tenant registration failed:', error)
    }
  }

  const handleCopyLink = () => {
    if (!createdTenant?.set_password_url) return
    void navigator.clipboard.writeText(createdTenant.set_password_url).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  /** Parse token from set_password_url and go to our set-password page in the same tab. */
  const goToSetPassword = () => {
    if (!createdTenant?.set_password_url) return
    try {
      const url = new URL(createdTenant.set_password_url, window.location.origin)
      const token = url.searchParams.get('token') ?? ''
      if (token) {
        navigate({
          to: '/set-password',
          search: { token },
        })
      } else {
        window.location.href = createdTenant.set_password_url
      }
    } catch {
      window.location.href = createdTenant.set_password_url
    }
  }

  const goToLogin = () => {
    if (createdTenant) {
      navigate({
        to: '/login',
        search: {},
      })
    }
  }

  // Show nothing while redirecting
  if (isAuthenticated) {
    return null
  }

  // C2 success: show set-password link; admin sets password via link, then logs in
  if (createdTenant) {
    const setPasswordUrl = createdTenant.set_password_url ?? ''
    const expiresAt = createdTenant.set_password_expires_at
      ? formatFullDateTime(createdTenant.set_password_expires_at)
      : null

    return (
      <AuthPageLayout>
        <AuthCard>
          <div className="flex flex-col items-center text-center">
            <CheckCircle className="h-5 w-5 text-status-ok" aria-hidden />
            <h1 className="mt-3 font-display text-xl font-semibold tracking-tight text-foreground">
              Tenant created
            </h1>
            <p className="mt-1 max-w-full truncate text-sm text-muted-foreground">
              {createdTenant.tenant_name}
            </p>
          </div>
          <dl className="mt-8 divide-y divide-border">
            <div className="flex items-baseline gap-4 py-3">
              <dt className="w-28 shrink-0 text-sm text-muted-foreground">Tenant code</dt>
              <dd className="min-w-0 font-mono text-sm text-foreground">
                {createdTenant.tenant_code}
              </dd>
            </div>
            <div className="flex items-baseline gap-4 py-3">
              <dt className="w-28 shrink-0 text-sm text-muted-foreground">Username</dt>
              <dd className="min-w-0 font-mono text-sm text-foreground">
                {createdTenant.admin_username}
              </dd>
            </div>
            <div className="flex items-baseline gap-4 py-3">
              <dt className="w-28 shrink-0 text-sm text-muted-foreground">Email</dt>
              <dd className="min-w-0 break-all text-sm text-foreground">
                {createdTenant.admin_email}
              </dd>
            </div>
            {expiresAt && (
              <div className="flex items-baseline gap-4 py-3">
                <dt className="w-28 shrink-0 text-sm text-muted-foreground">Link expires</dt>
                <dd className="text-xs text-muted-foreground">{expiresAt}</dd>
              </div>
            )}
          </dl>
          {setPasswordUrl ? (
            <>
              <div className="mt-5">
                <span className="text-sm font-medium text-foreground">Set-password link</span>
                <div className="mt-1.5 flex gap-2">
                  <Input
                    readOnly
                    value={setPasswordUrl}
                    className="flex-1 bg-muted/40 font-mono text-xs"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={handleCopyLink}
                    title={copied ? 'Copied!' : 'Copy link'}
                    aria-label={copied ? 'Copied!' : 'Copy link'}
                  >
                    <Copy className="w-4 h-4" />
                  </Button>
                </div>
              </div>
              <Button type="button" size="lg" onClick={goToSetPassword} className="mt-4 w-full">
                <KeyRound className="mr-2 h-4 w-4" />
                Set your password
              </Button>
            </>
          ) : (
            <p className="mt-5 bg-muted/40 px-3 py-2.5 text-sm text-muted-foreground">
              No set-password link was returned. Ensure the backend has{' '}
              <code className="bg-muted px-1 text-xs">SET_PASSWORD_BASE_URL</code> configured.
            </p>
          )}

          <div className="mt-8 flex flex-col items-center gap-4">
            <Button variant="outline" size="lg" onClick={goToLogin} className="w-full">
              Go to login
            </Button>
            <button
              type="button"
              onClick={() => {
                window.location.href = '/'
              }}
              className="inline-flex cursor-pointer items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
              aria-label="Back to home"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back to home
            </button>
          </div>
        </AuthCard>
      </AuthPageLayout>
    )
  }

  return (
    <AuthPageLayout>
      <AuthCard>
        {/* Title */}
        <h1 className="text-center font-display text-xl font-semibold tracking-tight text-foreground">
          Create tenant
        </h1>

        {/* Error Message */}
        {authState.error && (
          <div className="mt-6 bg-destructive/10 px-3 py-2.5">
            <p className="text-sm text-destructive">{authState.error}</p>
          </div>
        )}

        {/* Register Form */}
        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <div>
            <label
              htmlFor="tenant-name"
              className="mb-1.5 block text-sm font-medium text-foreground"
            >
              Tenant name
            </label>
            <Input
              id="tenant-name"
              type="text"
              value={tenantName}
              onChange={(e) => setTenantName(e.target.value)}
              required
              placeholder="Acme Corp"
            />
          </div>

          <div>
            <label
              htmlFor="tenant-code"
              className="mb-1.5 block text-sm font-medium text-foreground"
            >
              Tenant code
            </label>
            <Input
              id="tenant-code"
              type="text"
              value={tenantCode}
              onChange={(e) =>
                setTenantCode(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))
              }
              required
              placeholder="acme-corp"
              className="font-mono"
              pattern="[a-z0-9\-]+"
              title="3–15 characters: lowercase letters, numbers, and hyphens only"
            />
          </div>

          <Button
            type="submit"
            size="lg"
            disabled={authState.isLoading}
            isLoading={authState.isLoading}
            className="w-full"
          >
            {authState.isLoading ? 'Creating tenant…' : 'Create tenant'}
          </Button>
        </form>

        {/* Bottom links */}
        <div className="mt-8 flex flex-col items-center gap-2.5 text-center">
          <p className="text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link to="/login" search={{}} className="font-medium text-foreground hover:underline">
              Sign in
            </Link>
          </p>
          <button
            type="button"
            onClick={() => {
              window.location.href = '/'
            }}
            className="inline-flex cursor-pointer items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
            aria-label="Back to home"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to home
          </button>
        </div>
      </AuthCard>
    </AuthPageLayout>
  )
}
