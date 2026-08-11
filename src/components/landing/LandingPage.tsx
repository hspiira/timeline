import { Link } from '@tanstack/react-router'
import { ArrowRight } from 'lucide-react'

const PROJECT_NAME = 'Timeline'

/** Landing is always dark; wrap in .dark so dark: styles apply regardless of app theme */
export function LandingPage() {
  const year = new Date().getFullYear()

  return (
    <div className="dark min-h-screen h-screen flex flex-col bg-background overflow-auto">
      {/* Content */}
      <header className="relative z-10 flex items-center justify-between px-6 py-4 sm:px-8 shrink-0">
        <Link
          to="/"
          className="flex items-center gap-2.5 text-foreground/90 hover:text-foreground transition-all duration-300 hover:scale-[1.02] active:scale-[0.98]"
        >
          <img src="/logo.svg" alt="" className="w-8 h-8 opacity-90 transition-transform duration-300 hover:rotate-6" aria-hidden />
          <span className="font-display text-lg font-semibold tracking-tight">
            {PROJECT_NAME}
          </span>
        </Link>
        <Link
          to="/login"
          search={{}}
          className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-foreground/90 transition-all duration-300 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/30"
        >
          Sign in
        </Link>
      </header>

      <main className="relative z-10 flex flex-1 items-center justify-start px-6 sm:px-8 md:px-12 lg:px-16">
        <div className="w-full max-w-4xl flex flex-col md:flex-row md:items-center md:justify-between gap-10 md:gap-16 text-left">
          <div className="flex flex-col gap-5 max-w-xl">
            <h1
              className="font-display text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold text-foreground/95 tracking-tight animate-in fade-in slide-in-from-bottom-4 duration-700 [animation-fill-mode:both]"
              style={{ animationDelay: '100ms' }}
            >
              Events, subjects, and documents in one place.
            </h1>
            <p
              className="text-base sm:text-lg text-muted-foreground/90 animate-in fade-in slide-in-from-bottom-4 duration-600 [animation-fill-mode:both]"
              style={{ animationDelay: '250ms' }}
            >
              Track what matters. Timeline keeps your work organized and easy to find.
            </p>
          </div>
          <div
            className="flex shrink-0 md:pl-8 animate-in fade-in slide-in-from-bottom-4 duration-600 [animation-fill-mode:both]"
            style={{ animationDelay: '400ms' }}
          >
            <Link
              to="/login"
              search={{}}
              className="group inline-flex items-center justify-center gap-2 rounded-lg bg-white/[0.08] px-8 py-3.5 text-sm font-medium text-foreground backdrop-blur-sm transition-all duration-300 hover:bg-white/[0.14] hover:-translate-y-0.5 hover:shadow-[0_8px_30px_rgba(255,255,255,0.08)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/30 active:translate-y-0"
              style={{
                background: 'linear-gradient(to right, rgba(255,255,255,0.06), rgba(255,255,255,0.12))',
              }}
            >
              Get started
              <ArrowRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1" />
            </Link>
          </div>
        </div>
      </main>

      <footer className="relative z-10 shrink-0 px-6 py-4 sm:px-8">
        <p
          className="text-xs text-muted-foreground/80 animate-in fade-in duration-500 [animation-fill-mode:both]"
          style={{ animationDelay: '550ms' }}
        >
          © {year} {PROJECT_NAME}
        </p>
      </footer>
    </div>
  )
}
