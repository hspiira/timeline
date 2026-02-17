import { createFileRoute, useNavigate, Link } from '@tanstack/react-router'
import { useState } from 'react'
import { useStore } from '@tanstack/react-store'
import { ArrowLeft, CheckCircle, Copy, KeyRound } from 'lucide-react'
import { authStore, authActions } from '@/lib/auth-store'
import { useRedirectIfAuthenticated } from '@/lib/hooks'
import { AuthPageLayout } from '@/components/auth/AuthPageLayout'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

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
          search: { token, tenant: createdTenant.tenant_code },
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
        search: { tenant: createdTenant.tenant_code, redirect: undefined },
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
      ? new Date(createdTenant.set_password_expires_at).toLocaleString(undefined, {
          dateStyle: 'medium',
          timeStyle: 'short',
        })
      : null

    return (
      <AuthPageLayout>
        <div className="w-full max-w-md py-12">
          <div className="bg-card/80 backdrop-blur-md border border-white/10 shadow-xl rounded-lg p-8">
            <div className="flex justify-center mb-6">
              <img src="/logo.svg" alt="Timeline" className="w-16 h-16" />
            </div>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-none bg-primary/10 flex items-center justify-center shrink-0">
                <CheckCircle className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-foreground">Tenant created</h1>
                <p className="text-sm text-muted-foreground">{createdTenant.tenant_name}</p>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-4">
              Open the link below to set your admin password, then log in.
            </p>
            <dl className="space-y-0 mb-6">
              <div className="flex items-baseline gap-4 py-3 border-b border-border">
                <dt className="text-sm text-muted-foreground shrink-0 w-28">Tenant code</dt>
                <dd className="text-sm font-mono text-foreground min-w-0">{createdTenant.tenant_code}</dd>
              </div>
              <div className="flex items-baseline gap-4 py-3 border-b border-border">
                <dt className="text-sm text-muted-foreground shrink-0 w-28">Username</dt>
                <dd className="text-sm font-mono text-foreground min-w-0">{createdTenant.admin_username}</dd>
              </div>
              <div className="flex items-baseline gap-4 py-3 border-b border-border">
                <dt className="text-sm text-muted-foreground shrink-0 w-28">Email</dt>
                <dd className="text-sm text-foreground min-w-0 break-all">{createdTenant.admin_email}</dd>
              </div>
              {expiresAt && (
                <div className="flex items-baseline gap-4 py-3 border-b border-border">
                  <dt className="text-sm text-muted-foreground shrink-0 w-28">Link expires</dt>
                  <dd className="text-xs text-muted-foreground">{expiresAt}</dd>
                </div>
              )}
            </dl>
            {setPasswordUrl ? (
              <>
                <div className="mb-4">
                  <span className="text-sm text-muted-foreground">Set-password link</span>
                  <div className="mt-1 flex gap-2">
                    <Input
                      readOnly
                      value={setPasswordUrl}
                      className="font-mono text-xs flex-1 bg-muted/50"
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
                <Button
                  type="button"
                  onClick={goToSetPassword}
                  className="w-full"
                >
                  <KeyRound className="w-4 h-4 mr-2" />
                  Set your password
                </Button>
              </>
            ) : (
              <p className="text-sm text-muted-foreground mb-4">
                No set-password link was returned. Ensure the backend has <code className="text-xs bg-muted px-1 rounded">SET_PASSWORD_BASE_URL</code> configured.
              </p>
            )}
            <p className="text-sm text-muted-foreground mt-6 mb-2">After you’ve set your password:</p>
            <Button variant="secondary" onClick={goToLogin} className="w-full">
              Go to login
            </Button>
            <div className="mt-6 text-center">
              <button
                type="button"
                onClick={() => {
                  window.location.href = '/'
                }}
                className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                aria-label="Back to home"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to home
              </button>
            </div>
          </div>
        </div>
      </AuthPageLayout>
    )
  }

  return (
    <AuthPageLayout>
      <div className="w-full max-w-md py-12">
        <div className="bg-card/80 backdrop-blur-md border border-white/10 shadow-xl rounded-lg p-8">
          {/* Logo */}
          <div className="flex justify-center mb-6">
            <img src="/logo.svg" alt="Timeline" className="w-16 h-16" />
          </div>

          {/* Title */}
          <h1 className="text-2xl font-bold text-center mb-2 text-foreground">
            Create tenant
          </h1>
          <p className="text-center text-muted-foreground mb-6">
            Register your organisation. You’ll set the admin password via a link after creation.
          </p>

          {/* Error Message */}
          {authState.error && (
            <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 rounded-none">
              <p className="text-sm text-destructive">{authState.error}</p>
            </div>
          )}

          {/* Register Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="tenant-name"
                className="block text-sm font-medium text-foreground mb-1.5"
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
              <p className="mt-1 text-xs text-muted-foreground">
                Display name for your organisation
              </p>
            </div>

            <div>
              <label
                htmlFor="tenant-code"
                className="block text-sm font-medium text-foreground mb-1.5"
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
                pattern="[a-z0-9\-]+"
                title="3–15 characters: lowercase letters, numbers, and hyphens only"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                e.g. acme-corp · 3–15 characters
              </p>
            </div>

            <Button
              type="submit"
              disabled={authState.isLoading}
              isLoading={authState.isLoading}
              className="w-full"
            >
              {authState.isLoading ? 'Creating tenant...' : 'Create tenant'}
            </Button>
          </form>

          {/* Bottom links */}
          <div className="mt-6 flex flex-col items-center gap-3 text-center">
            <p className="text-sm text-muted-foreground">
              Already have an account?{' '}
              <Link
                to="/login"
                search={{ tenant: '', redirect: '/' }}
                className="text-foreground font-medium hover:underline"
              >
                Sign in
              </Link>
            </p>
            <button
              type="button"
              onClick={() => {
                window.location.href = '/'
              }}
              className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
              aria-label="Back to home"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to home
            </button>
          </div>
        </div>
      </div>
    </AuthPageLayout>
  )
}
