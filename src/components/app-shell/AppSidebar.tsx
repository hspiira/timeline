'use client'

import { Link, useRouterState } from '@tanstack/react-router'
import { useState } from 'react'
import {
  LayoutDashboard,
  Users,
  Calendar,
  GitBranch,
  Mail,
  FileCheck,
  Wrench,
  BarChart3,
  Activity,
  Settings,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'

function NavLink({
  to,
  icon: Icon,
  children,
  collapsed,
}: {
  to: string
  icon: React.ElementType
  children: React.ReactNode
  collapsed: boolean
}) {
  const router = useRouterState()
  const pathname = router.location.pathname
  const isActive = to === '/' ? pathname === '/' : pathname.startsWith(to)

  return (
    <Link
      to={to}
      className={cn(
        'flex items-center gap-2 text-sm font-medium transition-colors rounded-none',
        isActive
          ? 'bg-primary text-primary-foreground'
          : 'text-foreground/70 hover:text-foreground hover:bg-accent',
        collapsed ? 'justify-center px-2 py-2' : 'px-3 py-2'
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
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={cn(
        'flex flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-200',
        collapsed ? 'w-[52px]' : 'w-56',
        className
      )}
    >
      <div className="flex flex-1 flex-col gap-1 overflow-auto py-2">
        {/* Core */}
        <div className={!collapsed ? 'px-2' : 'px-1'}>
          {!collapsed && (
            <p className="mb-1 px-2 text-xs font-semibold text-muted-foreground">Core</p>
          )}
          <NavLink to="/" icon={LayoutDashboard} collapsed={collapsed}>
            Dashboard
          </NavLink>
          <NavLink to="/subjects" icon={Users} collapsed={collapsed}>
            Subjects
          </NavLink>
          <NavLink to="/events" icon={Calendar} collapsed={collapsed}>
            Events
          </NavLink>
          <NavLink to="/flows" icon={GitBranch} collapsed={collapsed}>
            Flows
          </NavLink>
          <NavLink to="/email-accounts" icon={Mail} collapsed={collapsed}>
            Email
          </NavLink>
        </div>

        <Separator orientation="horizontal" className="my-1" />

        {/* Integrity */}
        <div className={!collapsed ? 'px-2' : 'px-1'}>
          {!collapsed && (
            <p className="mb-1 px-2 text-xs font-semibold text-muted-foreground">Integrity</p>
          )}
          <NavLink to="/verify/tenant" icon={FileCheck} collapsed={collapsed}>
            Verify
          </NavLink>
          <NavLink to="/integrity/repairs" icon={Wrench} collapsed={collapsed}>
            Repairs
          </NavLink>
        </div>

        <Separator orientation="horizontal" className="my-1" />

        {/* Analytics */}
        <div className={!collapsed ? 'px-2' : 'px-1'}>
          {!collapsed && (
            <p className="mb-1 px-2 text-xs font-semibold text-muted-foreground">Analytics</p>
          )}
          <NavLink to="/projections" icon={BarChart3} collapsed={collapsed}>
            Projections
          </NavLink>
        </div>

        <Separator orientation="horizontal" className="my-1" />

        {/* System / Admin */}
        <div className={!collapsed ? 'px-2' : 'px-1'}>
          {!collapsed && (
            <p className="mb-1 px-2 text-xs font-semibold text-muted-foreground">System</p>
          )}
          <NavLink to="/connectors" icon={Activity} collapsed={collapsed}>
            Connectors
          </NavLink>
          <NavLink to="/settings" icon={Settings} collapsed={collapsed}>
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
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>
    </aside>
  )
}
