import { TanStackDevtools } from '@tanstack/react-devtools'
import type { QueryClient } from '@tanstack/react-query'
import { useQueryClient } from '@tanstack/react-query'
import {
  createRootRouteWithContext,
  HeadContent,
  Link,
  Scripts,
  useNavigate,
} from '@tanstack/react-router'
import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'
import { useStore } from '@tanstack/react-store'
import { Bell, LogOut } from 'lucide-react'
import { useEffect } from 'react'
import { AppSidebar } from '@/components/app-shell/AppSidebar'
import { GlobalSearch } from '@/components/header/GlobalSearch'
import { SettingsButton } from '@/components/header/SettingsButton'
import { TenantSelector } from '@/components/header/TenantSelector'
import { ThemeProvider } from '@/components/theme/theme-provider'
import { ThemeToggle } from '@/components/theme/theme-toggler'
import { ToastContainer } from '@/components/toast/ToastContainer'
import { ErrorBoundary } from '@/components/ui/ErrorBoundary'
import { NotFound } from '@/components/ui/NotFound'
import TanStackQueryDevtools from '@/integrations/tanstack-query/devtools'
import { getApiBaseUrl } from '@/lib/api-client'
import { authActions, authStore } from '@/lib/auth-store'
import appCss from '@/styles.css?url'

interface MyRouterContext {
  queryClient: QueryClient
}

export const Route = createRootRouteWithContext<MyRouterContext>()({
  notFoundComponent: () => <NotFound fullPage />,
  head: () => {
    const apiOrigin = new URL(getApiBaseUrl()).origin
    const csp = [
      "default-src 'self'",
      "script-src 'self'",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data:",
      `connect-src 'self' ${apiOrigin}`,
    ].join('; ')
    return {
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
        {
          httpEquiv: 'Content-Security-Policy',
          content: csp,
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
    }
  },

  shellComponent: RootDocument,
})

function RootDocument({ children }: { children: React.ReactNode }) {
  const authState = useStore(authStore)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

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
            {authState.user ? (
              <div className="flex flex-col h-screen overflow-hidden">
                <header className="z-40 flex h-16 shrink-0 items-center gap-4 border-b bg-background/80 backdrop-blur-md dark:bg-background dark:backdrop-blur-none px-4 sm:px-6 lg:px-8 w-full">
                  <Link to="/" className="flex items-center gap-2 group shrink-0">
                    <img
                      src="/logo.svg"
                      alt="Timeline"
                      className="w-8 h-8 transition-transform group-hover:scale-110"
                    />
                    <span className="text-xl font-bold text-foreground hidden sm:inline">
                      Timeline
                    </span>
                  </Link>
                  <div className="flex-1 flex justify-end items-center gap-2">
                    <GlobalSearch />
                    <TenantSelector />
                    <button
                      type="button"
                      className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-none transition-colors"
                      aria-label="Notifications"
                      title="Notifications (coming soon)"
                    >
                      <Bell className="w-5 h-5" />
                    </button>
                    <span className="text-sm font-medium text-muted-foreground hidden md:inline">
                      {authState.user.username}
                    </span>
                    <SettingsButton />
                    <ThemeToggle />
                    <button
                      type="button"
                      onClick={handleLogout}
                      className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-foreground/70 hover:text-foreground hover:bg-accent rounded-none transition-all"
                    >
                      <LogOut className="w-4 h-4" />
                      <span className="hidden sm:inline">Logout</span>
                    </button>
                  </div>
                </header>
                <div className="flex flex-1 min-h-0 min-w-0">
                  <AppSidebar />
                  <main className="flex-1 min-h-0 overflow-y-auto bg-background">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                      <ErrorBoundary onRetry={() => queryClient.invalidateQueries()}>
                        {children}
                      </ErrorBoundary>
                    </div>
                  </main>
                </div>
              </div>
            ) : (
              <ErrorBoundary onRetry={() => queryClient.invalidateQueries()}>
                {children}
              </ErrorBoundary>
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
