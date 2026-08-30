import { Link2 } from 'lucide-react'

/** Newest first. Each record links back to the one before it; the oldest is genesis. */
const RECORDS = [
  {
    time: '2026-03-02 09:41',
    type: 'payment',
    title: 'Rent paid, March',
    hash: 'a3f9…2c1d',
    prev: '7be2…90e4',
  },
  {
    time: '2026-03-01 16:07',
    type: 'document',
    title: 'Signed tenancy agreement',
    hash: '7be2…90e4',
    prev: '4d51…f08c',
  },
  {
    time: '2026-02-28 11:20',
    type: 'event',
    title: 'Initial offer sent',
    hash: '4d51…f08c',
    prev: 'genesis',
  },
]

export function RecordChain() {
  return (
    <div className="relative pl-9 select-none">
      <div className="absolute left-2 top-2 bottom-2 w-px bg-[#24dd7b]/25" aria-hidden />
      <div className="space-y-4">
        {RECORDS.map((r) => (
          <div key={r.hash} className="relative">
            <span
              className="absolute -left-7 top-6 h-1.5 w-1.5 -translate-x-1/2 rounded-full"
              style={{ background: '#24dd7b' }}
              aria-hidden
            />
            <div className="rounded-lg border border-white/10 bg-[#0a0f0d]/80 px-4 py-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[11px] tracking-wide text-muted-foreground/80">{r.time}</span>
                <span className="rounded border border-[#24dd7b]/30 bg-[#24dd7b]/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[#24dd7b]">
                  {r.type}
                </span>
              </div>
              <p className="mt-1.5 text-sm font-medium text-foreground">{r.title}</p>
              <div className="mt-2 flex items-center gap-1 text-[11px] text-muted-foreground/60">
                <span className="font-mono text-white/70">{r.hash}</span>
                <span className="px-0.5 text-muted-foreground/40" aria-hidden>
                  →
                </span>
                <span className="inline-flex items-center gap-1">
                  <Link2 className="h-3 w-3" />
                  {r.prev}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
