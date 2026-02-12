import { useNavigate } from '@tanstack/react-router'
import { Calendar, Tag, ArrowRight, Activity, SquarePen } from 'lucide-react'
import type { SubjectWithMetadata } from '@/hooks/useSubjects'
import { User, Users, Building2, ShoppingCart, FolderKanban, FileText, Package, type LucideIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'

// Helper to get icon and color for subject type
function getSubjectIcon(
  subjectType: string
): { icon: LucideIcon; bgColor: string; textColor: string; borderColor: string; headerBg: string } {
  const type = subjectType.toLowerCase()

  const iconMap: Record<string, { icon: LucideIcon; bgColor: string; textColor: string; borderColor: string; headerBg: string }> = {
    user: { icon: User, bgColor: 'bg-blue-100 dark:bg-blue-900/20', textColor: 'text-blue-600 dark:text-blue-400', borderColor: 'border-blue-200 dark:border-blue-800', headerBg: 'bg-gradient-to-r from-blue-50/50 to-blue-100/30 dark:from-blue-950/20 dark:to-blue-900/10' },
    users: { icon: Users, bgColor: 'bg-blue-100 dark:bg-blue-900/20', textColor: 'text-blue-600 dark:text-blue-400', borderColor: 'border-blue-200 dark:border-blue-800', headerBg: 'bg-gradient-to-r from-blue-50/50 to-blue-100/30 dark:from-blue-950/20 dark:to-blue-900/10' },
    customer: { icon: Building2, bgColor: 'bg-purple-100 dark:bg-purple-900/20', textColor: 'text-purple-600 dark:text-purple-400', borderColor: 'border-purple-200 dark:border-purple-800', headerBg: 'bg-gradient-to-r from-purple-50/50 to-purple-100/30 dark:from-purple-950/20 dark:to-purple-900/10' },
    order: { icon: ShoppingCart, bgColor: 'bg-green-100 dark:bg-green-900/20', textColor: 'text-green-600 dark:text-green-400', borderColor: 'border-green-200 dark:border-green-800', headerBg: 'bg-gradient-to-r from-green-50/50 to-green-100/30 dark:from-green-950/20 dark:to-green-900/10' },
    project: { icon: FolderKanban, bgColor: 'bg-orange-100 dark:bg-orange-900/20', textColor: 'text-orange-600 dark:text-orange-400', borderColor: 'border-orange-200 dark:border-orange-800', headerBg: 'bg-gradient-to-r from-orange-50/50 to-orange-100/30 dark:from-orange-950/20 dark:to-orange-900/10' },
    invoice: { icon: FileText, bgColor: 'bg-amber-100 dark:bg-amber-900/20', textColor: 'text-amber-600 dark:text-amber-400', borderColor: 'border-amber-200 dark:border-amber-800', headerBg: 'bg-gradient-to-r from-amber-50/50 to-amber-100/30 dark:from-amber-950/20 dark:to-amber-900/10' },
    shipment: { icon: Package, bgColor: 'bg-cyan-100 dark:bg-cyan-900/20', textColor: 'text-cyan-600 dark:text-cyan-400', borderColor: 'border-cyan-200 dark:border-cyan-800', headerBg: 'bg-gradient-to-r from-cyan-50/50 to-cyan-100/30 dark:from-cyan-950/20 dark:to-cyan-900/10' },
    package: { icon: Package, bgColor: 'bg-cyan-100 dark:bg-cyan-900/20', textColor: 'text-cyan-600 dark:text-cyan-400', borderColor: 'border-cyan-200 dark:border-cyan-800', headerBg: 'bg-gradient-to-r from-cyan-50/50 to-cyan-100/30 dark:from-cyan-950/20 dark:to-cyan-900/10' },
  }

  return iconMap[type] || { icon: Tag, bgColor: 'bg-gray-100 dark:bg-gray-900/20', textColor: 'text-gray-600 dark:text-gray-400', borderColor: 'border-gray-200 dark:border-gray-800', headerBg: 'bg-gradient-to-r from-gray-50/50 to-gray-100/30 dark:from-gray-950/20 dark:to-gray-900/10' }
}

interface SubjectsGridProps {
  data: SubjectWithMetadata[]
  onEdit?: (subject: SubjectWithMetadata) => void
}

export function SubjectsGrid({ data, onEdit }: SubjectsGridProps) {
  const navigate = useNavigate()

  const handleSubjectClick = (subjectId: string) => {
    navigate({ to: `/subjects/${subjectId}` })
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {data.map((subject) => {
        const { icon: Icon, bgColor, textColor, borderColor, headerBg } = getSubjectIcon(subject.subject_type)
        return (
          <div
            key={subject.id}
            onClick={() => handleSubjectClick(subject.id)}
            className={`bg-card/80 backdrop-blur-sm rounded-xs border ${borderColor} hover:border-opacity-100 transition-all hover:shadow-md cursor-pointer overflow-hidden group`}
          >
            {/* Header with icon and type */}
            <div className={`p-4 border-b ${borderColor} ${headerBg}`}>
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className={`w-10 h-10 rounded-xs ${bgColor} flex items-center justify-center flex-shrink-0`}>
                  <Icon className={`w-5 h-5 ${textColor}`} />
                </div>
                <div className="px-2 py-1 bg-muted rounded text-xs font-medium text-muted-foreground">
                  {subject.subject_type}
                </div>
              </div>

              {/* Subject ID */}
              <h3 className="font-semibold text-foreground truncate text-sm mb-1 group-hover:text-primary transition-colors">
                {subject.id}
              </h3>

              {/* External Reference */}
              {subject.external_ref && (
                <p className="text-xs text-muted-foreground truncate">
                  Ref: {subject.external_ref}
                </p>
              )}
            </div>

            {/* Body with metadata */}
            <div className="p-4 space-y-3">
              {/* Events Count */}
              <div className="flex items-center gap-2 text-xs">
                <Activity className="w-4 h-4 text-muted-foreground/60" />
                <span className="text-muted-foreground">
                  {subject.eventCount} event{subject.eventCount !== 1 ? 's' : ''}
                </span>
              </div>

              {/* Last Event Date */}
              {subject.lastEventDate && (
                <div className="flex items-center gap-2 text-xs">
                  <Calendar className="w-4 h-4 text-muted-foreground/60" />
                  <span className="text-muted-foreground">
                    Last event {new Date(subject.lastEventDate).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                    })}
                  </span>
                </div>
              )}
            </div>

            {/* Footer with action hint */}
            <div className="px-4 py-3 bg-muted/30 border-t border-border/30 flex items-center justify-between group-hover:bg-muted/50 transition-colors">
              <span className="text-xs font-medium text-muted-foreground">View details</span>
              <div className="flex items-center gap-2">
                <Button
                  onClick={(e) => {
                    e.stopPropagation()
                    onEdit?.(subject)
                  }}
                  variant="ghost"
                  size="sm"
                  title="Edit subject"
                >
                  <SquarePen className="w-4 h-4" />
                </Button>
                <ArrowRight className="w-4 h-4 text-muted-foreground/60 group-hover:text-primary transition-colors group-hover:translate-x-0.5" />
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
