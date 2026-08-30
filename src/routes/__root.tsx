import { TanStackDevtools } from '@tanstack/react-devtools'
import type { QueryClient } from '@tanstack/react-query'
import { useQueryClient } from '@tanstack/react-query'
import { createRootRouteWithContext, Link, Outlet, useNavigate } from '@tanstack/react-router'
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
import { authActions, authStore } from '@/lib/auth-store'

interface MyRouterContext {
  queryClient: QueryClient
}

export const Route = createRootRouteWithContext<MyRouterContext>()({
  notFoundComponent: () => <NotFound fullPage />,
  component: RootDocument,
})

function RootDocument() {
  const authState = useStore(authStore)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Initialize auth on mount
  useEffect(() => {
    authActions.initAuth()
  }, [])

  // A route chunk can 404 when a deploy replaces it while a tab holds the old
  // index.html. Reloading fetches the new one. Two things the previous version
  // missed: the event is cancelable and Vite rethrows unless preventDefault is
  // called, and a chunk that is genuinely gone would otherwise reload forever.
  useEffect(() => {
    const RELOAD_FLAG = 'timeline:chunk-reload'
    const onPreloadError = (event: Event) => {
      event.preventDefault()
      if (sessionStorage.getItem(RELOAD_FLAG)) return
      sessionStorage.setItem(RELOAD_FLAG, '1')
      window.location.reload()
    }
    window.addEventListener('vite:preloadError', onPreloadError)
    sessionStorage.removeItem(RELOAD_FLAG)
    return () => window.removeEventListener('vite:preloadError', onPreloadError)
  }, [])

  const handleLogout = () => {
    authActions.logout()
    navigate({ to: '/' })
  }

  return (
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
                <span className="text-xl font-bold text-foreground hidden sm:inline">Timeline</span>
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
                    <Outlet />
                  </ErrorBoundary>
                </div>
              </main>
            </div>
          </div>
        ) : (
          <ErrorBoundary onRetry={() => queryClient.invalidateQueries()}>
            <Outlet />
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
  )
}
