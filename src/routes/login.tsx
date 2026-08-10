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
    // Vestigial: sign-in no longer uses an organisation code. Kept only because ten
    // call sites still pass it; safe to drop along with those links.
    tenant: (search.tenant as string) || '',
    redirect: safeRedirectPath(search.redirect),
    sessionExpired: search.session_expired === '1',
  }),
})

/** Remembering the last organisation means a repeat user never sees the picker again. */
const LAST_ORG_KEY = 'timeline_last_tenant_id'

function readLastOrg(): string | null {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(LAST_ORG_KEY)
}

function rememberLastOrg(tenantId: string) {
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(LAST_ORG_KEY, tenantId)
  }
}

function LoginPage() {
  const navigate = useNavigate()
  const { redirect, sessionExpired } = Route.useSearch()
  const authState = useStore(authStore)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [mounted, setMounted] = useState(false)
  // Only populated when the email turns out to belong to several organisations.
  const [organisations, setOrganisations] = useState<
    { tenant_id: string; name: string }[]
  >([])
  const [chosenOrg, setChosenOrg] = useState<string>('')
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
      // If a picker is already showing, the user has chosen; otherwise work out
      // whether one is even needed. Most people belong to one organisation and
      // never see this.
      let tenantId = chosenOrg || undefined

      if (!tenantId) {
        const orgs = await authActions.organisationsForEmail(email)
        if (orgs.length > 1) {
          const remembered = readLastOrg()
          const known = orgs.find((o) => o.tenant_id === remembered)
          if (known) {
            tenantId = known.tenant_id
          } else {
            setOrganisations(orgs)
            setChosenOrg(orgs[0].tenant_id)
            return
          }
        }
        // Zero or one: send it without an organisation and let the server decide,
        // so an unknown email fails the same way a wrong password does.
      }

      await authActions.login(email, password, tenantId)
      if (tenantId) rememberLastOrg(tenantId)
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
                htmlFor="email"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                Email
              </label>
              <Input
                id="email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value)
                  // A different email may belong to different organisations.
                  setOrganisations([])
                  setChosenOrg('')
                }}
                required
                placeholder="you@company.com"
              />
            </div>

            {/* Shown only when this email belongs to more than one organisation. */}
            {organisations.length > 1 && (
              <div>
                <label
                  htmlFor="organisation"
                  className="mb-1.5 block text-sm font-medium text-foreground"
                >
                  Organisation
                </label>
                <select
                  id="organisation"
                  value={chosenOrg}
                  onChange={(e) => setChosenOrg(e.target.value)}
                  className="w-full rounded-none border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1"
                >
                  {organisations.map((o) => (
                    <option key={o.tenant_id} value={o.tenant_id}>
                      {o.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

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
