import { createFileRoute, useNavigate, Link } from '@tanstack/react-router'
import { useState } from 'react'
import { useStore } from '@tanstack/react-store'
import { ArrowLeft, CheckCircle } from 'lucide-react'
import { authStore, authActions } from '@/lib/auth-store'
import { useRedirectIfAuthenticated } from '@/lib/hooks'
import { AuthPageLayout } from '@/components/auth/AuthPageLayout'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

export const Route = createFileRoute('/register')({
  component: RegisterTenantPage,
})

/** Backend returns this after tenant creation; admin password is never returned (user sets it in the form). */
interface TenantCreationResult {
  tenant_id: string
  tenant_code: string
  tenant_name: string
  admin_username: string
}

function RegisterTenantPage() {
  const navigate = useNavigate()
  const authState = useStore(authStore)
  const [tenantCode, setTenantCode] = useState('')
  const [tenantName, setTenantName] = useState('')
  const [adminPassword, setAdminPassword] = useState('')
  const [showAdminPassword, setShowAdminPassword] = useState(false)
  const [createdTenant, setCreatedTenant] = useState<TenantCreationResult | null>(null)

  // Redirect if already logged in
  const isAuthenticated = useRedirectIfAuthenticated()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    authActions.clearError()

    try {
      const result = await authActions.registerTenant({
        code: tenantCode,
        name: tenantName,
        admin_initial_password: adminPassword.trim() || undefined,
      })

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

            <p className="text-sm text-muted-foreground mb-6">
              Use the password you entered to sign in.
            </p>

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

            <div>
              <label
                htmlFor="admin-password"
                className="block text-sm font-medium text-foreground mb-1.5"
              >
                Admin password
              </label>
              <div className="relative">
                <Input
                  id="admin-password"
                  type={showAdminPassword ? 'text' : 'password'}
                  value={adminPassword}
                  onChange={(e) => setAdminPassword(e.target.value)}
                  required
                  minLength={8}
                  placeholder="••••••••"
                  className="pr-10"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowAdminPassword(!showAdminPassword)}
                  className="absolute right-1 top-1/2 -translate-y-1/2 px-2 text-muted-foreground hover:text-foreground"
                  aria-label={showAdminPassword ? 'Hide password' : 'Show password'}
                >
                  {showAdminPassword ? (
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </Button>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                At least 8 characters. You will use this to sign in as the admin user.
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
