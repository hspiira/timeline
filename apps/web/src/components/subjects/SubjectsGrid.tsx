import { Link } from '@tanstack/react-router'
import { Activity, ArrowRight, Calendar, SquarePen } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/ui/StatusBadge'
import type { SubjectWithMetadata } from '@/hooks/useSubjects'
import { formatShortDate } from '@/lib/format-date'
import { getSubjectTypeThemeFromConfig } from '@/lib/subject-type-theme'
import type { components } from '@/lib/timeline-api'

type SubjectTypeListItem = components['schemas']['SubjectTypeListItem']

interface SubjectsGridProps {
  data: SubjectWithMetadata[]
  onEdit?: (subject: SubjectWithMetadata) => void
  /** Subject types from API (Settings → Subject types); used for icon, color, and label */
  subjectTypeConfig?: SubjectTypeListItem[]
}

function getDisplayName(subjectType: string, config?: SubjectTypeListItem[]): string {
  const found = config?.find((t) => t.type_name.toLowerCase() === subjectType.toLowerCase())
  return found?.display_name ?? subjectType
}

export function SubjectsGrid({ data, onEdit, subjectTypeConfig }: SubjectsGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {data.map((subject) => {
        const theme = getSubjectTypeThemeFromConfig(subject.subject_type, subjectTypeConfig)
        const { icon: Icon, bgColor, textColor, headerBg, configColor } = theme
        const typeLabel = getDisplayName(subject.subject_type, subjectTypeConfig)
        const useConfigColor = configColor != null && configColor !== ''
        return (
          <div
            key={subject.id}
            className={`relative bg-card/80 rounded-none border transition-all cursor-pointer overflow-hidden group hover:border-border/40 ${
              (subject.integrityStatus ?? '') === 'broken'
                ? 'border-status-warn/50 bg-status-warn/5'
                : 'border-border/25'
            }`}
            style={useConfigColor && configColor ? { borderColor: `${configColor}20` } : undefined}
          >
            {/* Header with icon and type */}
            <div
              className={`p-4 border-b border-border/25 ${useConfigColor ? '' : headerBg}`}
              style={
                useConfigColor && configColor
                  ? {
                      backgroundColor: `${configColor}15`,
                    }
                  : undefined
              }
            >
              <div className="flex items-start justify-between gap-3 mb-3">
                <div
                  className={`w-10 h-10 rounded-none flex items-center justify-center flex-shrink-0 ${useConfigColor ? '' : bgColor}`}
                  style={
                    useConfigColor && configColor
                      ? {
                          backgroundColor: `${configColor}20`,
                          color: configColor,
                        }
                      : undefined
                  }
                >
                  <Icon className={`w-5 h-5 ${useConfigColor ? '' : textColor}`} />
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge
                    status={
                      (subject.integrityStatus ?? 'unknown') as 'valid' | 'broken' | 'unknown'
                    }
                    dotOnly
                  />
                  <span className="px-2 py-1 bg-muted rounded-none text-xs font-medium text-muted-foreground">
                    {typeLabel}
                  </span>
                </div>
              </div>

              {/* Subject name: display name when set, else id */}
              <h3
                className="font-semibold text-foreground truncate text-sm mb-1 group-hover:text-primary transition-colors"
                title={subject.display_name?.trim() ? subject.id : undefined}
              >
                {subject.display_name?.trim() || subject.id}
              </h3>

              {/* ID when display name is shown; external ref when present */}
              {subject.display_name?.trim() && (
                <p className="text-xs text-muted-foreground truncate font-mono">ID: {subject.id}</p>
              )}
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
            <div className="px-4 py-3 bg-muted/30 border-t border-border/20 flex items-center justify-between group-hover:bg-muted/50 transition-colors">
              <Link
                to="/subjects/$subjectId"
                params={{ subjectId: subject.id }}
                search={{ tab: 'events', event_id: undefined }}
                className="text-xs font-medium text-muted-foreground after:absolute after:inset-0"
              >
                View details
              </Link>
              <div className="relative flex items-center gap-2">
                <Button
                  onClick={() => onEdit?.(subject)}
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
