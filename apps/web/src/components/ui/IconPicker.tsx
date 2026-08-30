import { ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { CURATED_ICONS, getCuratedIcon, ICON_NAMES } from '@/lib/curated-lucide-icons'
import { cn } from '@/lib/utils'

interface IconPickerProps {
  value: string
  onChange: (iconName: string) => void
  disabled?: boolean
  allowClear?: boolean
}

export function IconPicker({
  value,
  onChange,
  disabled = false,
  allowClear = true,
}: IconPickerProps) {
  const [open, setOpen] = useState(false)
  const CurrentIcon = getCuratedIcon(value)

  const handleSelect = (name: string) => {
    onChange(name)
    setOpen(false)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          disabled={disabled}
          className={cn(
            'flex items-center gap-2 w-full h-10 pl-2.5 pr-3 py-2 rounded-none border border-input bg-background text-sm text-left transition-colors',
            'hover:bg-muted/50 hover:border-muted-foreground/30',
            disabled && 'opacity-50 cursor-not-allowed',
          )}
        >
          <span className="flex items-center justify-center w-8 h-8 shrink-0 rounded-md border border-border bg-muted/30">
            {CurrentIcon ? (
              <CurrentIcon className="w-4 h-4 text-muted-foreground" />
            ) : (
              <span className="text-xs font-medium text-muted-foreground">—</span>
            )}
          </span>
          <span className="flex-1 text-sm text-muted-foreground">
            {value ? value : 'Select icon'}
          </span>
          <ChevronDown className="w-4 h-4 shrink-0 text-muted-foreground" />
        </button>
      </PopoverTrigger>
      <PopoverContent
        className="w-auto max-w-[min(320px,calc(100vw-2rem)] max-h-[min(320px,70vh)] overflow-hidden flex flex-col p-3 rounded-lg border border-border shadow-lg"
        align="start"
        sideOffset={6}
        avoidCollisions={true}
        collisionPadding={12}
      >
        <div className="grid grid-cols-6 sm:grid-cols-7 gap-1.5 max-h-56 overflow-y-auto">
          {allowClear && (
            <button
              type="button"
              onClick={() => handleSelect('')}
              className={cn(
                'flex flex-col items-center justify-center gap-0.5 min-w-[2.25rem] min-h-[2.25rem] rounded-md border-2 shrink-0 transition-all',
                !value
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border hover:border-muted-foreground/40 hover:bg-muted/50 text-muted-foreground',
              )}
            >
              <span className="text-[10px] font-medium uppercase tracking-wider">None</span>
            </button>
          )}
          {ICON_NAMES.map((name) => {
            const Icon = CURATED_ICONS[name]
            if (!Icon) return null
            const isSelected =
              value === name || (value && value.toLowerCase() === name.toLowerCase())
            return (
              <button
                key={name}
                type="button"
                onClick={() => handleSelect(name)}
                title={name}
                className={cn(
                  'flex items-center justify-center min-w-[2.25rem] min-h-[2.25rem] rounded-md border-2 shrink-0 transition-all',
                  isSelected
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-transparent hover:border-muted-foreground/30 hover:bg-muted/50 text-muted-foreground hover:text-foreground',
                )}
              >
                <Icon className="w-4 h-4" />
              </button>
            )
          })}
        </div>
      </PopoverContent>
    </Popover>
  )
}
