import { Link } from '@tanstack/react-router'
import { ArrowRight } from 'lucide-react'
import { TimelineBand } from './TimelineBand'

const PROJECT_NAME = 'Timeline'

/** Landing is always dark; wrap in .dark so dark: styles apply regardless of app theme */
export function LandingPage() {
  const year = new Date().getFullYear()

  return (
    <div className="dark relative min-h-screen lg:h-screen lg:overflow-hidden flex flex-col bg-background overflow-x-hidden">
      <div className="landing-backdrop" aria-hidden>
        <div className="landing-glow" />
        <div className="landing-floor" />
      </div>

      <header className="relative z-10 flex shrink-0 items-center justify-between px-6 sm:px-10 py-5">
        <Link
          to="/"
          className="flex items-center gap-2.5 text-foreground/90 hover:text-foreground transition-all duration-300 hover:scale-[1.02] active:scale-[0.98]"
        >
          <img
            src="/logo.svg"
            alt=""
            className="w-8 h-8 opacity-90 transition-transform duration-300 hover:rotate-6"
            aria-hidden
          />
          <span className="font-display text-lg font-semibold tracking-tight">{PROJECT_NAME}</span>
        </Link>
        <Link to="/login" search={{}} className="landing-ghost-btn">
          Sign in
        </Link>
      </header>

      <main className="relative z-10 flex flex-1 flex-col justify-center gap-12 px-6 sm:px-10 py-8">
        <div className="w-full">
          <div className="flex max-w-2xl flex-col items-start gap-6">
            <h1
              className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-foreground animate-in fade-in slide-in-from-bottom-4 duration-700 [animation-fill-mode:both]"
              style={{ animationDelay: '160ms' }}
            >
              See the story, <span className="landing-accent">not the noise</span>.
            </h1>

            <p
              className="max-w-lg text-base sm:text-lg leading-relaxed text-muted-foreground animate-in fade-in slide-in-from-bottom-4 duration-600 [animation-fill-mode:both]"
              style={{ animationDelay: '280ms' }}
            >
              Timeline connects every customer signal, business event, and workflow into one living
              history. No tabs. No detective work. Just a sequence that holds.
            </p>

            <div
              className="pt-1 animate-in fade-in slide-in-from-bottom-4 duration-600 [animation-fill-mode:both]"
              style={{ animationDelay: '400ms' }}
            >
              <Link to="/login" search={{}} className="landing-cta group">
                Get started
                <ArrowRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1" />
              </Link>
            </div>
          </div>
        </div>

        <div
          className="w-full animate-in fade-in duration-700 [animation-fill-mode:both]"
          style={{ animationDelay: '520ms' }}
        >
          <TimelineBand />
        </div>
      </main>

      <footer className="relative z-10 shrink-0 px-6 sm:px-10 py-5">
        <p className="text-xs text-muted-foreground/70">
          © {year} {PROJECT_NAME}
        </p>
      </footer>
    </div>
  )
}
