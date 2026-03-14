import { createFileRoute, useNavigate, Link } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { useStore } from '@tanstack/react-store'
import { ArrowLeft, Eye, EyeOff } from 'lucide-react'
import { authStore, authActions } from '@/lib/auth-store'
import { useRedirectIfAuthenticated } from '@/lib/hooks'
import { AuthPageLayout } from '@/components/auth/AuthPageLayout'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

/** Only allow relative app paths to avoid open redirects */
function safeRedirectPath(raw: unknown): string | undefined {
  const s = typeof raw === 'string' ? raw.trim() : ''
  if (!s || !s.startsWith('/') || s.startsWith('//')) return undefined
  return s
}

export const Route = createFileRoute('/login')({
  component: LoginPage,
  validateSearch: (search: Record<string, unknown>) => ({
    tenant: (search.tenant as string) || '',
    redirect: safeRedirectPath(search.redirect),
  }),
})

function LoginPage() {
  const navigate = useNavigate()
  const { tenant, redirect } = Route.useSearch()
  const authState = useStore(authStore)
  const [tenantCode, setTenantCode] = useState(tenant)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  // Path-only for navigate() to avoid search schema mismatches; pathname is enough to return to the right page
  const redirectTo = redirect ?? '/'
  const redirectPath = redirectTo.includes('?') ? redirectTo.slice(0, redirectTo.indexOf('?')) : redirectTo

  // Redirect if already logged in (to intended page or dashboard)
  const isAuthenticated = useRedirectIfAuthenticated(redirectPath)

  // Only reflect loading state after mount so SSR and first client render match (avoids hydration mismatch).
  const showLoading = mounted && authState.isLoading

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    authActions.clearError()

    try {
      await authActions.login(username, password, tenantCode)
      navigate({ to: redirectPath })
    } catch (error) {
      console.error('Login failed:', error)
    }
  }

  // Show nothing while redirecting
  if (isAuthenticated) {
    return null
  }

  return (
    <AuthPageLayout>
      <div className="w-full max-w-md">
        <div className="bg-card/80 backdrop-blur-md border border-border shadow-xl p-8 [border-radius:var(--radius)]">
          {/* Logo */}
          <div className="flex justify-center mb-6">
            <img src="/logo.svg" alt="Timeline" className="w-16 h-16" />
          </div>

          {/* Title */}
          <h1 className="text-2xl font-bold text-center mb-6 text-foreground">
            Sign In
          </h1>

          {/* Error Message */}
          {authState.error && (
            <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 rounded-none">
              <p className="text-sm text-destructive">
                {authState.error}
              </p>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="tenant-code"
                className="block text-sm font-medium text-foreground mb-1.5"
              >
                Organisation code
              </label>
              <p className="text-xs text-muted-foreground mb-1.5">
                From your admin or invite email.
              </p>
              <Input
                id="tenant-code"
                type="text"
                value={tenantCode}
                onChange={(e) => setTenantCode(e.target.value)}
                required
                placeholder="e.g. acme-corp"
              />
            </div>

            <div>
              <label
                htmlFor="username"
                className="block text-sm font-medium text-foreground mb-1.5"
              >
                Username
              </label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                placeholder="username"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-foreground mb-1.5"
              >
                Password
              </label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••"
                  className="pr-10"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-1 top-1/2 -translate-y-1/2 px-2 text-muted-foreground hover:text-foreground"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            <Button
              type="submit"
              disabled={showLoading}
              isLoading={showLoading}
              className="w-full"
            >
              {showLoading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>

          {/* Bottom links */}
          <div className="mt-6 flex flex-col items-center gap-3 text-center">
            <p className="text-sm text-muted-foreground">
              Don't have an account?{' '}
              <Link
                to="/register"
                className="text-foreground font-medium hover:underline"
              >
                Register your tenant
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
