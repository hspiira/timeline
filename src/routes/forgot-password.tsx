import { createFileRoute, Link } from '@tanstack/react-router'
import { AuthPageLayout } from '@/components/auth/AuthPageLayout'
import { Button } from '@/components/ui/button'
import { ArrowLeft, KeyRound } from 'lucide-react'

export const Route = createFileRoute('/forgot-password')({
  component: ForgotPasswordPage,
})

function ForgotPasswordPage() {
  return (
    <AuthPageLayout>
      <div className="w-full max-w-md">
        <div className="bg-card/80 backdrop-blur-md border border-border shadow-xl p-8 [border-radius:var(--radius)]">
          <div className="flex justify-center mb-6">
            <KeyRound className="w-12 h-12 text-muted-foreground" />
          </div>
          <h1 className="text-xl font-bold text-center mb-2 text-foreground">
            Forgot password
          </h1>
          <p className="text-sm text-muted-foreground text-center mb-6">
            Password reset is not yet available. Contact your administrator to reset your password.
          </p>
          <Link to="/login" search={{ tenant: '', redirect: undefined, sessionExpired: false }}>
            <Button variant="outline" className="w-full">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Sign In
            </Button>
          </Link>
        </div>
      </div>
    </AuthPageLayout>
  )
}
