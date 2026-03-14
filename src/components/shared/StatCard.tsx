import { type LucideIcon, TrendingUp } from "lucide-react"

type StatCardProps = {
    label: string
    value: number | string
    subtitle?: string
    subtext?: string
    icon: LucideIcon
    variant?: 'default' | 'compact' | 'hero'
    color?: string
}

export function StatCard({
    label,
    value,
    subtitle,
    subtext,
    icon: Icon,
    variant = 'default',
    color
}: StatCardProps) {
    if (variant === 'compact') {
      const displaySubtext = subtext || subtitle
      return (
        <div className="bg-card/50 rounded-none border border-border/50 p-3">
          <div className="flex items-center gap-2 mb-2">
            <Icon className={`w-4 h-4 ${color || 'text-muted-foreground'}`} />
            <span className="text-xs font-medium text-muted-foreground">{label}</span>
          </div>
          <p className="text-lg font-semibold text-foreground">{value}</p>
          {displaySubtext && <p className="text-xs text-muted-foreground mt-1">{displaySubtext}</p>}
        </div>
      )
    }

    const displaySubtitle = subtitle || subtext
    const isHero = variant === 'hero'

    return (
        <div
            className={`
                group relative overflow-hidden
                rounded-none border border-border/60
                bg-card/80
                transition-all duration-300
                hover:border-[var(--dashboard-accent)]/40 hover:bg-card
                ${isHero ? 'p-6 md:p-8' : 'p-5'}
            `}
            style={{
                borderLeftWidth: '3px',
                borderLeftColor: 'var(--dashboard-accent)',
            }}
        >
            <div className={`flex ${isHero ? 'flex-col md:flex-row md:items-end md:justify-between' : 'flex-col'} gap-4`}>
                <div>
                    <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-1">
                        {label}
                    </p>
                    <p className={`font-display font-bold text-foreground tabular-nums ${isHero ? 'text-4xl md:text-5xl' : 'text-2xl'}`}>
                        {value}
                    </p>
                    {displaySubtitle && (
                        <p className="text-xs text-muted-foreground flex items-center gap-1 mt-2">
                            <TrendingUp className="w-3 h-3 opacity-70" />
                            {displaySubtitle}
                        </p>
                    )}
                </div>
                <div
                    className={`
                        flex items-center justify-center
                        w-10 h-10 md:w-12 md:h-12
                        rounded-none
                        bg-[var(--dashboard-accent-muted)]
                        text-[var(--dashboard-accent)]
                        ${isHero ? 'self-start md:self-auto' : ''}
                    `}
                >
                    <Icon className={isHero ? 'w-5 h-5 md:w-6 md:h-6' : 'w-5 h-5'} strokeWidth={1.75} />
                </div>
            </div>
        </div>
    )
}
