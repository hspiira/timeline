import { useCallback, useEffect, useRef, useState } from 'react'

const DWELL_MS = 5200

const SLIDES = [
  {
    at: 4,
    label: 'Context',
    title: 'Events are only useful when they have context.',
    body: 'Timeline adds the missing connective tissue between systems, people, and decisions.',
  },
  {
    at: 22,
    label: 'Connectors',
    title: 'Records arrive on their own.',
    body: 'Gmail, Outlook and IMAP connectors write events into the history without anyone typing them.',
  },
  {
    at: 40,
    label: 'Documents',
    title: 'Files stay with their event.',
    body: 'A signed contract is attached to the event that produced it, not filed away somewhere separate.',
  },
  {
    at: 58,
    label: 'Integrity',
    title: 'Nothing is edited quietly.',
    body: 'Each event is hashed onto the one before it, so a later change to the record shows up.',
  },
  {
    at: 77,
    label: 'History',
    title: 'Rewind to any moment.',
    body: 'Ask what a subject looked like on a past date and read the state its events produced.',
  },
  {
    at: 96,
    label: 'Privacy',
    title: 'Erase or export on request.',
    body: 'Anonymise or delete a subject without breaking the chain that vouches for everything else.',
  },
]

export function TimelineBand() {
  const [index, setIndex] = useState(0)
  const [paused, setPaused] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const schedule = useCallback(() => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => setIndex((i) => (i + 1) % SLIDES.length), DWELL_MS)
  }, [])

  useEffect(() => {
    if (paused || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    schedule()
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
  }, [index, paused, schedule])

  const active = SLIDES[index]

  return (
    <div
      className="landing-band"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <div className="landing-ruler">
        <div className="landing-ticks" />
        <div className="landing-baseline" />
        <div className="landing-progress" style={{ width: `${active.at}%` }} />
        <div className="landing-playhead" style={{ left: `${active.at}%` }} />

        {SLIDES.map((slide, i) => (
          <button
            type="button"
            key={slide.label}
            onClick={() => setIndex(i)}
            style={{ left: `${slide.at}%` }}
            className={`landing-marker${i === index ? ' is-active' : ''}${i < index ? ' is-past' : ''}`}
            aria-label={`Show ${slide.label}`}
            aria-current={i === index}
          >
            <span className="landing-marker-dot" />
            <span className="landing-marker-label">{slide.label}</span>
          </button>
        ))}
      </div>

      <div className="landing-band-detail">
        <div
          key={index}
          className="animate-in fade-in slide-in-from-bottom-2 duration-500 [animation-fill-mode:both]"
        >
          <p className="landing-detail-title">{active.title}</p>
          <p className="landing-detail-text">{active.body}</p>
        </div>
      </div>
    </div>
  )
}
