/**
 * Shared layout for login/register: forced dark mode, plain background.
 */
export function AuthPageLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="dark min-h-screen flex flex-col bg-background">
      <div className="relative z-10 flex flex-1 items-center justify-center p-6">
        {children}
      </div>
    </div>
  )
}
