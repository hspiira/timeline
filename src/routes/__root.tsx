import {
  HeadContent,
  Scripts,
  createRootRouteWithContext,
  Link,
  useRouterState,
  useNavigate,
} from '@tanstack/react-router'
import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'
import { TanStackDevtools } from '@tanstack/react-devtools'
import { useStore } from '@tanstack/react-store'
import { useEffect } from 'react'
import { LogOut, LayoutDashboard, Users, Calendar, Mail, GitBranch } from 'lucide-react'

import TanStackQueryDevtools from '@/integrations/tanstack-query/devtools'
import { authStore, authActions } from '@/lib/auth-store'
import { ThemeToggle } from '@/components/theme/theme-toggler'
import { ThemeProvider } from '@/components/theme/theme-provider'
import { SettingsButton } from '@/components/header/SettingsButton'
import { GlobalSearch } from '@/components/header/GlobalSearch'
import { ToastContainer } from '@/components/toast/ToastContainer'
import { ErrorBoundary } from '@/components/ui/ErrorBoundary'
import { NotFound } from '@/components/ui/NotFound'

import appCss from '@/styles.css?url'

import type { QueryClient } from '@tanstack/react-query'

interface MyRouterContext {
  queryClient: QueryClient
}

export const Route = createRootRouteWithContext<MyRouterContext>()({
  notFoundComponent: () => <NotFound fullPage />,
  head: () => ({
    meta: [
      {
        charSet: 'utf-8',
      },
      {
        name: 'viewport',
        content: 'width=device-width, initial-scale=1',
      },
      {
        title: 'Timeline',
      },
    ],
    links: [
      {
        rel: 'stylesheet',
        href: appCss,
      },
      {
        rel: 'icon',
        type: 'image/svg+xml',
        href: '/logo.svg',
      },
    ],
  }),

  shellComponent: RootDocument,
})

function NavLink({
  to,
  icon: Icon,
  children,
}: {
  to: string
  icon: React.ElementType
  children: React.ReactNode
}) {
  const router = useRouterState()
  const pathname = router.location.pathname
  const isActive = to === '/' ? pathname === '/' : pathname.startsWith(to)

  return (
    <Link
      to={to}
      className={`flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-none transition-all ${
        isActive
          ? 'bg-primary text-primary-foreground'
          : 'text-foreground/70 hover:text-foreground hover:bg-accent'
      }`}
    >
      <Icon className="w-4 h-4" />
      {children}
    </Link>
  )
}

function RootDocument({ children }: { children: React.ReactNode }) {
  const authState = useStore(authStore)
  const navigate = useNavigate()

  // Initialize auth on mount
  useEffect(() => {
    authActions.initAuth()
  }, [])

  // Recover from failed dynamic route chunk (e.g. after deploy or stale cache)
  useEffect(() => {
    const onPreloadError = () => {
      window.location.reload()
    }
    window.addEventListener('vite:preloadError', onPreloadError)
    return () => window.removeEventListener('vite:preloadError', onPreloadError)
  }, [])

  const handleLogout = () => {
    authActions.logout()
    navigate({ to: '/' })
  }

  return (
    <html lang="en" className="h-full">
      <head>
        <HeadContent />
      </head>
      <body className="h-full overflow-x-hidden">
        <ThemeProvider defaultTheme="system" storageKey="timeline-theme">
          <ErrorBoundary>
          {/* Header - only show on non-auth pages */}
          {authState.user && (
            <header className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between items-center h-16">
                  <div className="flex items-center gap-8">
                    <Link to="/" className="flex items-center gap-2 group">
                      <img src="/logo.svg" alt="Timeline" className="w-8 h-8 transition-transform group-hover:scale-110" />
                      <span className="text-xl font-bold text-foreground">
                        Timeline
                      </span>
                    </Link>

                    <nav className="hidden md:flex gap-1">
                      <NavLink to="/" icon={LayoutDashboard}>
                        Dashboard
                      </NavLink>
                      <NavLink to="/subjects" icon={Users}>
                        Subjects
                      </NavLink>
                      <NavLink to="/events" icon={Calendar}>
                        Events
                      </NavLink>
                      <NavLink to="/flows" icon={GitBranch}>
                        Flows
                      </NavLink>
                      <NavLink to="/email-accounts" icon={Mail}>
                        Email
                      </NavLink>
                    </nav>
                    <GlobalSearch />
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-muted-foreground">
                      {authState.user.username}
                    </span>
                    <SettingsButton />
                    <ThemeToggle />
                    <button
                      onClick={handleLogout}
                      className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-foreground/70 hover:text-foreground hover:bg-accent rounded-none transition-all"
                    >
                      <LogOut className="w-4 h-4" />
                      Logout
                    </button>
                  </div>
                </div>
              </div>
            </header>
          )}

          {authState.user ? (
            <main className="pt-8 min-h-[calc(100vh-4rem)] bg-background">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                {children}
              </div>
            </main>
          ) : (
            children
          )}

          <ToastContainer />
          </ErrorBoundary>

          <TanStackDevtools
            config={{
              position: 'bottom-right',
            }}
            plugins={[
              {
                name: 'Tanstack Router',
                render: <TanStackRouterDevtoolsPanel />,
              },
              TanStackQueryDevtools,
            ]}
          />
        </ThemeProvider>
        <Scripts />
      </body>
    </html>
  )
}
