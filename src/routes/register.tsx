import { createFileRoute, useNavigate, Link } from '@tanstack/react-router'
import { useState } from 'react'
import { useStore } from '@tanstack/react-store'
import { ArrowLeft, CheckCircle, AlertTriangle, Copy, Check } from 'lucide-react'
import { authStore, authActions } from '@/lib/auth-store'
import { useRedirectIfAuthenticated } from '@/lib/hooks'
import { AuthPageLayout } from '@/components/auth/AuthPageLayout'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

export const Route = createFileRoute('/register')({
  component: RegisterTenantPage,
})

interface TenantCreationResult {
  tenant_id: string
  tenant_code: string
  tenant_name: string
  admin_username: string
  admin_password: string
}

function RegisterTenantPage() {
  const navigate = useNavigate()
  const authState = useStore(authStore)
  const [tenantCode, setTenantCode] = useState('')
  const [tenantName, setTenantName] = useState('')
  const [createdTenant, setCreatedTenant] = useState<TenantCreationResult | null>(null)
  const [copiedPassword, setCopiedPassword] = useState(false)

  const copyPassword = () => {
    if (createdTenant) {
      navigator.clipboard.writeText(createdTenant.admin_password)
      setCopiedPassword(true)
      setTimeout(() => setCopiedPassword(false), 2000)
    }
  }

  // Redirect if already logged in
  const isAuthenticated = useRedirectIfAuthenticated()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    authActions.clearError()

    try {
      const result = await authActions.registerTenant({
        code: tenantCode,
        name: tenantName,
      })

      // Show the admin credentials
      setCreatedTenant(result)
    } catch (error) {
      console.error('Tenant registration failed:', error)
    }
  }

  const handleContinueToLogin = () => {
    if (createdTenant) {
      // Navigate to login with the tenant code pre-filled
      navigate({
        to: '/login',
        search: { tenant: createdTenant.tenant_code },
      })
    }
  }

  // Show nothing while redirecting
  if (isAuthenticated) {
    return null
  }

  // Show success screen with admin credentials
  if (createdTenant) {
    return (
      <AuthPageLayout>
        <div className="w-full max-w-md py-12">
          <div className="bg-card/80 backdrop-blur-md border border-white/10 shadow-xl rounded-lg p-8">
            {/* Logo */}
            <div className="flex justify-center mb-6">
              <img src="/logo.svg" alt="Timeline" className="w-16 h-16" />
            </div>

            {/* Success Header */}
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-none bg-primary/10 flex items-center justify-center shrink-0">
                <CheckCircle className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-foreground">Tenant Created</h1>
                <p className="text-sm text-muted-foreground">{createdTenant.tenant_name}</p>
              </div>
            </div>

            {/* Tenant Details */}
            <div className="space-y-3 mb-6">
              <div className="flex items-center justify-between py-2 border-b border-border">
                <span className="text-sm text-muted-foreground">Tenant Code</span>
                <code className="text-sm font-mono text-foreground">{createdTenant.tenant_code}</code>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-border">
                <span className="text-sm text-muted-foreground">Admin Username</span>
                <code className="text-sm font-mono text-foreground">{createdTenant.admin_username}</code>
              </div>
            </div>

            {/* Password with Warning */}
            <div className="bg-muted/50 border border-border rounded-none p-4 mb-6">
              <div className="flex items-start gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                <p className="text-xs text-muted-foreground">
                  Save this password now. It won't be shown again.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-sm font-mono text-foreground bg-card px-3 py-2 rounded-none border border-border break-all">
                  {createdTenant.admin_password}
                </code>
                <button
                  onClick={copyPassword}
                  className="p-2 hover:bg-muted rounded-none transition-colors shrink-0"
                  title="Copy password"
                >
                  {copiedPassword ? (
                    <Check className="w-4 h-4 text-primary" />
                  ) : (
                    <Copy className="w-4 h-4 text-muted-foreground" />
                  )}
                </button>
              </div>
            </div>

            {/* Continue Button */}
            <Button onClick={handleContinueToLogin} className="w-full">
              Continue to Login
            </Button>

            {/* Bottom links */}
            <div className="mt-6 flex flex-col items-center gap-3 text-center">
              <Link
                to="/"
                className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to home
              </Link>
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
            Create Your Organization
          </h1>
          <p className="text-center text-muted-foreground mb-6">
            Set up a new tenant for your team
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
                Organization Name
              </label>
              <Input
                id="tenant-name"
                type="text"
                value={tenantName}
                onChange={(e) => setTenantName(e.target.value)}
                required
                placeholder="Acme Corporation"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                Display name for your organization
              </p>
            </div>

            <div>
              <label
                htmlFor="tenant-code"
                className="block text-sm font-medium text-foreground mb-1.5"
              >
                Tenant Code
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
                pattern="[a-z0-9-]+"
                title="Lowercase letters, numbers, and hyphens only"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                Unique identifier for your organization (lowercase, no spaces)
              </p>
            </div>

            <Button
              type="submit"
              disabled={authState.isLoading}
              isLoading={authState.isLoading}
              className="w-full"
            >
              {authState.isLoading ? 'Creating organization...' : 'Create Organization'}
            </Button>
          </form>

          {/* Bottom links */}
          <div className="mt-6 flex flex-col items-center gap-3 text-center">
            <p className="text-sm text-muted-foreground">
              Already have an account?{' '}
              <Link
                to="/login"
                search={{ tenant: '' }}
                className="text-foreground font-medium hover:underline"
              >
                Sign in
              </Link>
            </p>
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to home
            </Link>
          </div>
        </div>
      </div>
    </AuthPageLayout>
  )
}
