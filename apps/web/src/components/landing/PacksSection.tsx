import { Link } from '@tanstack/react-router'
import { ArrowRight, Boxes, PenTool, Shield } from 'lucide-react'

const STEPS = [
  {
    icon: Boxes,
    title: 'Pick a pack',
    body: 'A pack is a data bundle: schemas, event types, document categories, and workflows for one domain. Tenancy, lending, and employment proof ship as reference packs.',
  },
  {
    icon: PenTool,
    title: 'Or model your own',
    body: 'Define subjects, events, and documents in a plain JSON manifest. No code and no plugin needed. The schema becomes the whole interface.',
  },
  {
    icon: Shield,
    title: 'Records become verifiable',
    body: 'Every event is hash-chained and sealed. The offline verifier lets any third party prove the history was never altered.',
  },
]

export function PacksSection() {
  return (
    <section id="packs" className="w-full scroll-mt-6 px-6 sm:px-10 py-14 sm:py-16">
      <div className="max-w-6xl">
        <h2 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
          One tamper-evident engine, any domain.
        </h2>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-muted-foreground">
          Timeline is the open-source record core. Domain packs turn it into something specific: a
          tenancy ledger, a loan file with court-ready evidence, an employment proof an employer can
          verify. Swap the pack, keep the guarantees.
        </p>

        <div className="mt-10 grid gap-6 sm:grid-cols-3">
          {STEPS.map((step) => (
            <div
              key={step.title}
              className="landing-step rounded-xl border border-white/10 bg-white/[0.02] p-6"
            >
              <step.icon className="h-6 w-6 text-[#24dd7b]" aria-hidden />
              <h3 className="mt-4 font-display text-lg font-semibold text-foreground">
                {step.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-wrap items-center gap-4">
          <Link to="/register" search={{}} className="landing-cta group">
            Create an account
            <ArrowRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-1" />
          </Link>
          <span className="text-sm text-muted-foreground/80">
            Self-host, open source, Apache-2.0. No lock-in.
          </span>
        </div>
      </div>
    </section>
  )
}
