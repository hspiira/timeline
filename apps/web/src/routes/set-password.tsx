import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, CheckCircle } from 'lucide-react'
import { useEffect, useId, useState } from 'react'
import { AuthPageLayout } from '@/components/auth/AuthPageLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { timelineApi } from '@/lib/api-client'

export const Route = createFileRoute('/set-password')({
  component: SetPasswordPage,
  validateSearch: (search: Record<string, unknown>) => ({
    // Token only. The organisation is derived server-side from the redeemed
    // token, so carrying an organisation code here served no purpose.
    token: typeof search.token === 'string' ? search.token : '',
  }),
})

const SET_PASSWORD_GENERIC_ERROR =
  'Please check your password and try again. Use at least 8 characters and make sure both fields match.'
const SET_PASSWORD_LINK_ERROR =
  'Invalid or expired link. Request a new link from your administrator.'

function getSetPasswordErrorMessage(apiError: unknown): string {
  const detail = (apiError as { detail?: string | Array<{ loc?: unknown[]; msg?: string }> })
    ?.detail
  if (detail == null) return SET_PASSWORD_LINK_ERROR

  // HTTPValidationError: detail is array of { loc, msg }
  if (Array.isArray(detail)) {
    const hasPasswordField = detail.some(
      (d) =>
        Array.isArray(d.loc) && d.loc.some((x) => String(x).toLowerCase().includes('password')),
    )
    if (hasPasswordField) return SET_PASSWORD_GENERIC_ERROR
    return SET_PASSWORD_LINK_ERROR
  }

  // detail as string (e.g. "body.password: String should have at least 8 characters")
  const s = String(detail).toLowerCase()
  if (
    s.includes('password') ||
    s.includes('body.') ||
    s.includes('validation') ||
    s.includes('at least 8')
  ) {
    return SET_PASSWORD_GENERIC_ERROR
  }

  return SET_PASSWORD_LINK_ERROR
}

function SetPasswordPage() {
  const passwordConfirmId = useId()
  const passwordId = useId()
  const navigate = useNavigate()
  const { token } = Route.useSearch()
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (!token) {
      setError('Invalid or expired link. Request a new link from your administrator.')
    }
  }, [token])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!token) return
    const p = password.trim()
    const pc = passwordConfirm.trim()
    if (p.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    if (p !== pc) {
      setError('Passwords do not match.')
      return
    }
    setLoading(true)
    try {
      const { error: apiError } = await timelineApi.auth.setInitialPassword({
        token,
        password: p,
        password_confirm: pc,
      })
      if (apiError) {
        const msg = getSetPasswordErrorMessage(apiError)
        setError(msg)
        return
      }
      setSuccess(true)
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const goToLogin = () => {
    navigate({
      to: '/login',
      search: {},
    })
  }

  if (success) {
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
                <h1 className="text-lg font-bold text-foreground">Password set</h1>
                <p className="text-sm text-muted-foreground">You can now log in.</p>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-6">
              Use username <strong>admin</strong> and your new password to sign in.
            </p>
            <Button onClick={goToLogin} className="w-full">
              Go to Login
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

  if (!token) {
    return (
      <AuthPageLayout>
        <div className="w-full max-w-md py-12">
          <div className="bg-card/80 backdrop-blur-md border border-white/10 shadow-xl rounded-lg p-8">
            <div className="flex justify-center mb-6">
              <img src="/logo.svg" alt="Timeline" className="w-16 h-16" />
            </div>
            <h1 className="text-lg font-bold text-foreground mb-2">Invalid link</h1>
            <p className="text-sm text-muted-foreground mb-6">{error}</p>
            <Link to="/login" search={{}}>
              <Button variant="outline" className="w-full">
                Go to Login
              </Button>
            </Link>
          </div>
        </div>
      </AuthPageLayout>
    )
  }

  return (
    <AuthPageLayout>
      <div className="w-full max-w-md py-12">
        <div className="bg-card/80 backdrop-blur-md border border-white/10 shadow-xl rounded-lg p-8">
          <div className="flex justify-center mb-6">
            <img src="/logo.svg" alt="Timeline" className="w-16 h-16" />
          </div>
          <h1 className="text-2xl font-bold text-center mb-2 text-foreground">Set your password</h1>
          <p className="text-center text-muted-foreground mb-6">
            Choose a password for your admin account (min 8 characters).
          </p>

          {error && (
            <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 rounded-none">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor={passwordId}
                className="block text-sm font-medium text-foreground mb-1.5"
              >
                Password
              </label>
              <div className="relative">
                <Input
                  id={passwordId}
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
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
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      aria-hidden="true"
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      aria-hidden="true"
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </Button>
              </div>
            </div>
            <div>
              <label
                htmlFor={passwordConfirmId}
                className="block text-sm font-medium text-foreground mb-1.5"
              >
                Confirm password
              </label>
              <Input
                id={passwordConfirmId}
                type="password"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                required
                minLength={8}
                placeholder="••••••••"
              />
            </div>
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? 'Setting password...' : 'Set password'}
            </Button>
          </form>

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
