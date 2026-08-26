'use client'

import { Link, useRouterState } from '@tanstack/react-router'
import { useStore } from '@tanstack/react-store'
import {
  Activity,
  BarChart3,
  Calendar,
  ChevronLeft,
  ChevronRight,
  FileCheck,
  GitBranch,
  LayoutDashboard,
  Mail,
  Settings,
  Users,
  Wrench,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { useHasSystemAccess } from '@/hooks/useHasSystemAccess'
import { authStore } from '@/lib/auth-store'
import { cn } from '@/lib/utils'

const SIDEBAR_COLLAPSED_KEY = 'sidebar-collapsed'

function NavLink({
  to,
  icon: Icon,
  children,
  collapsed,
  title,
}: {
  to: string
  icon: React.ElementType
  children: React.ReactNode
  collapsed: boolean
  title?: string
}) {
  const router = useRouterState()
  const pathname = router.location.pathname
  const isActive = to === '/' ? pathname === '/' : pathname.startsWith(to)
  const label = title ?? (typeof children === 'string' ? children : '')

  return (
    <Link
      to={to}
      title={collapsed ? label : undefined}
      className={cn(
        'flex items-center gap-2 text-sm font-medium transition-colors rounded-none',
        isActive
          ? 'bg-primary text-primary-foreground'
          : 'text-foreground/70 hover:text-foreground hover:bg-accent',
        collapsed ? 'justify-center px-2 py-2' : 'px-3 py-2',
      )}
    >
      <Icon className="w-4 h-4 shrink-0" />
      {!collapsed && <span>{children}</span>}
    </Link>
  )
}

interface AppSidebarProps {
  className?: string
}

export function AppSidebar({ className }: AppSidebarProps) {
  const authState = useStore(authStore)
  const hasSystemAccess = useHasSystemAccess(!!authState.user)
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false
    return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true'
  })

  useEffect(() => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(collapsed))
  }, [collapsed])

  return (
    <aside
      className={cn(
        'flex flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-200 shrink-0 h-full',
        collapsed ? 'w-[52px]' : 'w-56',
        className,
      )}
    >
      <div className="flex flex-1 flex-col gap-1 overflow-y-auto py-2">
        {/* Core: Dashboard, Subjects, Events only */}
        <div className={!collapsed ? 'px-2' : 'px-1'}>
          {!collapsed && (
            <p className="mb-1 px-2 text-xs font-semibold text-muted-foreground">Core</p>
          )}
          <NavLink to="/" icon={LayoutDashboard} collapsed={collapsed} title="Dashboard">
            Dashboard
          </NavLink>
          <NavLink to="/subjects" icon={Users} collapsed={collapsed} title="Subjects">
            Subjects
          </NavLink>
          <NavLink to="/events" icon={Calendar} collapsed={collapsed} title="Events">
            Events
          </NavLink>
        </div>

        <Separator orientation="horizontal" className="my-1" />

        {/* Integrity */}
        <div className={!collapsed ? 'px-2' : 'px-1'}>
          {!collapsed && (
            <p className="mb-1 px-2 text-xs font-semibold text-muted-foreground">Integrity</p>
          )}
          <NavLink to="/verify/tenant" icon={FileCheck} collapsed={collapsed} title="Verify">
            Verify
          </NavLink>
          <NavLink to="/integrity/repairs" icon={Wrench} collapsed={collapsed} title="Repairs">
            Repairs
          </NavLink>
        </div>

        <Separator orientation="horizontal" className="my-1" />

        {/* Analytics */}
        <div className={!collapsed ? 'px-2' : 'px-1'}>
          {!collapsed && (
            <p className="mb-1 px-2 text-xs font-semibold text-muted-foreground">Analytics</p>
          )}
          <NavLink to="/projections" icon={BarChart3} collapsed={collapsed} title="Projections">
            Projections
          </NavLink>
        </div>

        <Separator orientation="horizontal" className="my-1" />

        {/* System: Connectors (gated), Flows, Email, Settings */}
        <div className={!collapsed ? 'px-2' : 'px-1'}>
          {!collapsed && (
            <p className="mb-1 px-2 text-xs font-semibold text-muted-foreground">System</p>
          )}
          {hasSystemAccess !== false && (
            <NavLink to="/connectors" icon={Activity} collapsed={collapsed} title="Connectors">
              Connectors
            </NavLink>
          )}
          <NavLink to="/flows" icon={GitBranch} collapsed={collapsed} title="Flows">
            Flows
          </NavLink>
          <NavLink to="/email-accounts" icon={Mail} collapsed={collapsed} title="Email">
            Email
          </NavLink>
          <NavLink to="/settings" icon={Settings} collapsed={collapsed} title="Settings">
            Settings
          </NavLink>
        </div>
      </div>

      <div className="border-t border-sidebar-border p-2">
        <Button
          variant="ghost"
          size="icon"
          className="w-full"
          onClick={() => setCollapsed((c) => !c)}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
      </div>
    </aside>
  )
}
