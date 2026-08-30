import { Link } from '@tanstack/react-router'
import { ArrowRight, Boxes, Server, ShieldCheck } from 'lucide-react'
import { PacksSection } from './PacksSection'
import { RecordChain } from './RecordChain'

const PROJECT_NAME = 'Timeline'

/** Landing is always dark; wrap in .dark so dark: styles apply regardless of app theme */
export function LandingPage() {
  const year = new Date().getFullYear()

  return (
    <div className="dark relative min-h-screen flex flex-col bg-background overflow-x-hidden">
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
            className="w-8 h-8 -ml-2 opacity-90 transition-transform duration-300 hover:rotate-6"
            aria-hidden
          />
          <span className="font-display text-lg font-semibold tracking-tight">{PROJECT_NAME}</span>
        </Link>
        <nav className="flex items-center gap-3">
          <a href="#packs" className="landing-ghost-btn hidden sm:inline-flex">
            How packs work
          </a>
          <Link to="/login" search={{}} className="landing-ghost-btn">
            Sign in
          </Link>
        </nav>
      </header>

      <main className="relative z-10 flex flex-1 flex-col">
        <section className="flex w-full flex-1 flex-col justify-center gap-12 px-6 sm:px-10 py-10 lg:flex-row lg:items-center lg:justify-start lg:gap-16">
          <div className="flex max-w-xl flex-col items-start gap-6">
            <h1
              className="font-display text-4xl sm:text-5xl lg:text-[3.4rem] lg:leading-[1.05] font-bold tracking-tight text-foreground animate-in fade-in slide-in-from-bottom-4 duration-700 [animation-fill-mode:both]"
              style={{ animationDelay: '140ms' }}
            >
              Records that no one can <span className="landing-accent">silently change</span>.
            </h1>

            <p
              className="max-w-lg text-base sm:text-lg leading-relaxed text-muted-foreground animate-in fade-in slide-in-from-bottom-4 duration-600 [animation-fill-mode:both]"
              style={{ animationDelay: '260ms' }}
            >
              Timeline is an open-source record engine. Every event links to the one before it, so a
              later change to any record shows up. Drop in a domain pack for rent, loans, or
              employment proof, or run it on your own data.
            </p>

            <div
              className="pt-1 flex flex-wrap items-center gap-4 animate-in fade-in slide-in-from-bottom-4 duration-600 [animation-fill-mode:both]"
              style={{ animationDelay: '380ms' }}
            >
              <Link to="/register" search={{}} className="landing-cta group">
                Create an account
                <ArrowRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1" />
              </Link>
              <a href="#packs" className="landing-ghost-btn">
                See how packs work
              </a>
            </div>

            <div
              className="flex flex-wrap items-center gap-x-6 gap-y-2 pt-2 text-xs text-muted-foreground/70 animate-in fade-in duration-600 [animation-fill-mode:both]"
              style={{ animationDelay: '480ms' }}
            >
              <span className="inline-flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5" /> Independently verifiable
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Server className="w-3.5 h-3.5" /> Self-host
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Boxes className="w-3.5 h-3.5" /> Apache-2.0
              </span>
            </div>
          </div>

          <div
            className="w-full max-w-md lg:w-[26rem] animate-in fade-in slide-in-from-bottom-4 duration-700 [animation-fill-mode:both]"
            style={{ animationDelay: '300ms' }}
          >
            <RecordChain />
          </div>
        </section>
      </main>

      <hr className="relative z-10 mx-6 sm:mx-10 border-white/10" />

      <div className="relative z-10">
        <PacksSection />
      </div>

      <footer className="relative z-10 shrink-0 px-6 sm:px-10 py-6">
        <p className="text-xs text-muted-foreground/70">
          © {year} {PROJECT_NAME}, open source
        </p>
      </footer>
    </div>
  )
}
