import { useEffect } from 'react'
import { createFileRoute, Outlet, useLocation, useNavigate } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { useHasAuditAccess } from '@/hooks/useHasAuditAccess'
import type { LucideIcon } from 'lucide-react'
import { ShieldCheck, ShieldOff, Braces, Zap, Users, KeyRound, Layers, FolderOpen, ClipboardList, GitBranch, Link2, FileText } from 'lucide-react'

type NavItem = { path: string; label: string; icon: LucideIcon; description: string }

const SETTINGS_GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: 'Access control',
    items: [
      { path: '/settings/roles', label: 'Roles', icon: ShieldCheck, description: 'Manage roles and their permissions' },
      { path: '/settings/permissions', label: 'Permissions', icon: ShieldOff, description: 'Manage system permissions' },
      { path: '/settings/users', label: 'Users', icon: Users, description: 'Manage user permissions and roles' },
    ],
  },
  {
    label: 'Data model',
    items: [
      { path: '/settings/schemas', label: 'Event Schemas', icon: Braces, description: 'Manage JSON schemas' },
      { path: '/settings/event-transition-rules', label: 'Transition rules', icon: GitBranch, description: 'Require prior event types before creating an event' },
      { path: '/settings/subject-types', label: 'Subject Types', icon: Layers, description: 'Configure subject types and attributes' },
      { path: '/settings/relationship-kinds', label: 'Relationship kinds', icon: Link2, description: 'Allowed relationship types when linking subjects' },
    ],
  },
  {
    label: 'Documents',
    items: [
      { path: '/settings/document-categories', label: 'Document Categories', icon: FolderOpen, description: 'Configure document categories and retention' },
    ],
  },
  {
    label: 'Automation',
    items: [
      { path: '/settings/workflows', label: 'Workflows', icon: Zap, description: 'Automation & triggers' },
      { path: '/settings/naming-templates', label: 'Naming templates', icon: FileText, description: 'Flow, subject & document name templates' },
    ],
  },
  {
    label: 'Audit',
    items: [
      { path: '/settings/audit-log', label: 'Audit log', icon: ClipboardList, description: 'View tenant audit log' },
    ],
  },
  {
    label: 'Integrations',
    items: [
      { path: '/settings/oauth-providers', label: 'OAuth Providers', icon: KeyRound, description: 'Email OAuth credentials' },
    ],
  },
]

export const Route = createFileRoute('/settings')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  component: SettingsLayout,
})

function SettingsLayout() {
  const authState = useRequireAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const hasAuditAccess = useHasAuditAccess(!!authState.user)

  const pathname = location.pathname.replace(/\/$/, '') || '/'

  useEffect(() => {
    if (pathname === '/settings') {
      navigate({ to: '/settings/roles' })
    }
  }, [pathname, navigate])

  if (!authState.user) {
    return null
  }

  const isActive = (path: string) => pathname.startsWith(path)

  return (
    <div className="flex flex-col lg:flex-row gap-4 lg:gap-6 items-start">
      {/* Settings sub-nav: page-level list, not a second sidebar */}
      <div className="w-full lg:w-64 lg:shrink-0 bg-muted/30">
        <div className="p-3 lg:p-4 lg:sticky lg:top-16 lg:h-fit">
          <nav className="space-y-4">
            {SETTINGS_GROUPS.map((group) => {
              const items = group.items.filter((item) => {
                if (item.path === '/settings/audit-log') return hasAuditAccess === true
                return true
              })
              if (items.length === 0) return null
              return (
                <div key={group.label}>
                  <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5 px-3">
                    {group.label}
                  </div>
                  <div className="space-y-0.5">
                    {items.map((item) => {
                      const Icon = item.icon
                      const active = isActive(item.path)
                      return (
                        <button
                          key={item.path}
                          onClick={() => navigate({ to: item.path })}
                          className={`w-full flex items-center gap-3 px-3 py-1.5 rounded-none transition-colors text-left border-l-2 ${
                            active ? 'border-primary bg-primary/5' : 'border-transparent hover:bg-muted'
                          }`}
                        >
                          <Icon className="w-4 h-4 shrink-0 text-muted-foreground" />
                          <div className="flex-1 min-w-0">
                            <div className={`text-sm font-medium ${active ? 'text-foreground' : 'text-foreground/80'}`}>
                              {item.label}
                            </div>
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </nav>
        </div>
      </div>

      {/* Content — child routes provide their own heading (no redundant "Settings" h2) */}
      <div className="flex-1 min-w-0 w-full">
        <Outlet />
      </div>
    </div>
  )
}
