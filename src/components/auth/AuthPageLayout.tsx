/**
 * Shared layout for login/register: forced dark mode + same bg image as landing for uniformity.
 */
export function AuthPageLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="dark min-h-screen flex flex-col bg-background">
      {/* Same animated GIF as landing */}
      <div
        className="pointer-events-none fixed inset-0 z-0"
        aria-hidden
      >
        <div
          className="absolute inset-0 bg-cover bg-center bg-no-repeat opacity-[0.24]"
          style={{ backgroundImage: 'url(/images/hero-03.gif)' }}
        />
      </div>

      {/* Soft overlay */}
      <div
        className="pointer-events-none fixed inset-0 z-[1] bg-background/60"
        aria-hidden
      />

      {/* Subtle grid */}
      <div
        className="pointer-events-none fixed inset-0 z-[2] opacity-[0.04]"
        aria-hidden
        style={{
          backgroundImage: `
            linear-gradient(to right, currentColor 1px, transparent 1px),
            linear-gradient(to bottom, currentColor 1px, transparent 1px)
          `,
          backgroundSize: '8px 8px',
        }}
      />
      <div
        className="pointer-events-none fixed inset-0 z-[2] opacity-[0.12]"
        aria-hidden
        style={{
          background:
            'radial-gradient(ellipse 70% 50% at 50% 45%, var(--dashboard-accent-muted), transparent 65%)',
        }}
      />

      <div className="relative z-10 flex flex-1 items-center justify-center p-6">
        {children}
      </div>
    </div>
  )
}
