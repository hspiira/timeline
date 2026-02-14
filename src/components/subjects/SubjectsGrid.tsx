import { useNavigate } from '@tanstack/react-router'
import { Calendar, ArrowRight, Activity, SquarePen } from 'lucide-react'
import type { SubjectWithMetadata } from '@/hooks/useSubjects'
import { Button } from '@/components/ui/button'
import { getSubjectTypeTheme } from '@/lib/subject-type-theme'
import { formatShortDate } from '@/lib/format-date'

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
        const { icon: Icon, bgColor, textColor, borderColor, headerBg } = getSubjectTypeTheme(subject.subject_type)
        return (
          <div
            key={subject.id}
            onClick={() => handleSubjectClick(subject.id)}
            className={`bg-card/80 backdrop-blur-sm rounded-none border ${borderColor} hover:border-opacity-100 transition-all hover:shadow-md cursor-pointer overflow-hidden group`}
          >
            {/* Header with icon and type */}
            <div className={`p-4 border-b ${borderColor} ${headerBg}`}>
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className={`w-10 h-10 rounded-none ${bgColor} flex items-center justify-center flex-shrink-0`}>
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
                    Last event {formatShortDate(subject.lastEventDate)}
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
