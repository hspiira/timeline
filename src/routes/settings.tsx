import { createFileRoute, Outlet, useLocation, useNavigate } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { useHasAuditAccess } from '@/hooks/useHasAuditAccess'
import { Shield, Database, Zap, Users, KeyRound, Layers, FolderOpen, ClipboardList, GitBranch, Link2, FileText } from 'lucide-react'

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

  if (!authState.user) {
    return null
  }

  const pathname = location.pathname
  const isActive = (path: string) => pathname.startsWith(path)

  const menuItems = [
    {
      path: '/settings/roles',
      label: 'Roles',
      icon: Shield,
      description: 'Manage roles and their permissions',
    },
    {
      path: '/settings/permissions',
      label: 'Permissions',
      icon: Database,
      description: 'Manage system permissions',
    },
    {
      path: '/settings/users',
      label: 'Users',
      icon: Users,
      description: 'Manage user permissions and roles',
    },
    {
      path: '/settings/schemas',
      label: 'Event Schemas',
      icon: Database,
      description: 'Manage JSON schemas',
    },
    {
      path: '/settings/event-transition-rules',
      label: 'Transition rules',
      icon: GitBranch,
      description: 'Require prior event types before creating an event',
    },
    {
      path: '/settings/subject-types',
      label: 'Subject Types',
      icon: Layers,
      description: 'Configure subject types and attributes',
    },
    {
      path: '/settings/relationship-kinds',
      label: 'Relationship kinds',
      icon: Link2,
      description: 'Allowed relationship types when linking subjects',
    },
    {
      path: '/settings/document-categories',
      label: 'Document Categories',
      icon: FolderOpen,
      description: 'Configure document categories and retention',
    },
    {
      path: '/settings/workflows',
      label: 'Workflows',
      icon: Zap,
      description: 'Automation & triggers',
    },
    {
      path: '/settings/naming-templates',
      label: 'Naming templates',
      icon: FileText,
      description: 'Flow, subject & document name templates',
    },
    {
      path: '/settings/audit-log',
      label: 'Audit log',
      icon: ClipboardList,
      description: 'View tenant audit log',
    },
    {
      path: '/settings/oauth-providers',
      label: 'OAuth Providers',
      icon: KeyRound,
      description: 'Email OAuth credentials',
    },
  ]

  return (
    <div className="flex flex-col lg:flex-row gap-4 lg:gap-6 items-start">
      {/* Sidebar */}
      <div className="w-full lg:w-64 lg:shrink-0">
        <div className="p-3 lg:p-4 lg:sticky lg:top-16 lg:h-fit rounded-none">
          <h2 className="text-md font-semibold text-foreground mb-4">Settings</h2>
          <nav className="space-y-0.5">
            {menuItems
            .filter((item) => {
              if (item.path === '/settings/audit-log') return hasAuditAccess === true
              return true
            })
            .map((item) => {
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
          </nav>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 w-full">
        <Outlet />
      </div>
    </div>
  )
}
