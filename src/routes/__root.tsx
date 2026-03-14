import {
  HeadContent,
  Scripts,
  createRootRouteWithContext,
  Link,
  useNavigate,
} from '@tanstack/react-router'
import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'
import { TanStackDevtools } from '@tanstack/react-devtools'
import { useStore } from '@tanstack/react-store'
import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { LogOut, Bell } from 'lucide-react'

import TanStackQueryDevtools from '@/integrations/tanstack-query/devtools'
import { authStore, authActions } from '@/lib/auth-store'
import { ThemeToggle } from '@/components/theme/theme-toggler'
import { ThemeProvider } from '@/components/theme/theme-provider'
import { SettingsButton } from '@/components/header/SettingsButton'
import { GlobalSearch } from '@/components/header/GlobalSearch'
import { TenantSelector } from '@/components/header/TenantSelector'
import { ToastContainer } from '@/components/toast/ToastContainer'
import { ErrorBoundary } from '@/components/ui/ErrorBoundary'
import { NotFound } from '@/components/ui/NotFound'
import { AppSidebar } from '@/components/app-shell/AppSidebar'

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
              <header className="z-40 flex h-16 shrink-0 items-center gap-4 border-b bg-background/80 backdrop-blur-md px-4 sm:px-6 lg:px-8 w-full">
                <Link to="/" className="flex items-center gap-2 group shrink-0">
                  <img src="/logo.svg" alt="Timeline" className="w-8 h-8 transition-transform group-hover:scale-110" />
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
                    <ErrorBoundary
                      onRetry={() => queryClient.invalidateQueries()}
                    >
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
