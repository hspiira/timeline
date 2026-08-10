import { createFileRoute, useNavigate, Link } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { useStore } from '@tanstack/react-store'
import { ArrowLeft, Eye, EyeOff } from 'lucide-react'
import { authStore, authActions } from '@/lib/auth-store'
import { useRedirectIfAuthenticated } from '@/lib/hooks'
import { AuthPageLayout } from '@/components/auth/AuthPageLayout'
import { AuthCard } from '@/components/auth/AuthCard'
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
    sessionExpired: search.session_expired === '1',
  }),
})

function LoginPage() {
  const navigate = useNavigate()
  const { tenant, redirect, sessionExpired } = Route.useSearch()
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
      <AuthCard>
          {/* Title */}
          <h1 className="text-center font-display text-xl font-semibold tracking-tight text-foreground">
            Sign in
          </h1>

          {/* Session expired message */}
          {sessionExpired && !authState.error && (
            <div className="mt-6 bg-muted/40 px-3 py-2.5 text-sm text-muted-foreground">
              Session expired. Please sign in again.
            </div>
          )}
          {/* Error Message */}
          {authState.error && (
            <div className="mt-6 bg-destructive/10 px-3 py-2.5">
              <p className="text-sm text-destructive">
                {authState.error}
              </p>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="mt-8 space-y-4">
            <div>
              <label
                htmlFor="tenant-code"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                Organisation code
              </label>
              <Input
                id="tenant-code"
                type="text"
                value={tenantCode}
                onChange={(e) => setTenantCode(e.target.value)}
                required
                placeholder="acme-corp"
                className="font-mono"
              />
            </div>

            <div>
              <label
                htmlFor="username"
                className="mb-1.5 block text-sm font-medium text-foreground"
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
              <div className="mb-1.5 flex items-baseline justify-between gap-4">
                <label
                  htmlFor="password"
                  className="text-sm font-medium text-foreground"
                >
                  Password
                </label>
                <Link
                  to="/forgot-password"
                  className="text-xs text-muted-foreground transition-colors hover:text-foreground hover:underline"
                >
                  Forgot password?
                </Link>
              </div>
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
              size="lg"
              disabled={showLoading}
              isLoading={showLoading}
              className="w-full"
            >
              {showLoading ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>

          {/* Bottom links */}
          <div className="mt-8 flex flex-col items-center gap-2.5 text-center">
            <p className="text-sm text-muted-foreground">
              Don't have an account?{' '}
              <Link
                to="/register"
                className="font-medium text-foreground hover:underline"
              >
                Register your tenant
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
