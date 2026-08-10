import { useState } from 'react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

const PRESET_COLORS = [
  '#3b82f6',
  '#8b5cf6',
  '#ec4899',
  '#ef4444',
  '#f97316',
  '#eab308',
  '#22c55e',
  '#14b8a6',
  '#06b6d4',
  '#6366f1',
  '#64748b',
  '#78716c',
]

interface ColorSwatchPickerProps {
  value: string
  onChange: (hex: string) => void
  disabled?: boolean
  allowClear?: boolean
}

export function ColorSwatchPicker({
  value,
  onChange,
  disabled = false,
  allowClear = true,
}: ColorSwatchPickerProps) {
  const [open, setOpen] = useState(false)
  const normalizedValue = value?.trim().toLowerCase() || ''
  const isPreset = PRESET_COLORS.some((c) => c.toLowerCase() === normalizedValue)

  const handleSelect = (hex: string) => {
    onChange(hex)
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
            disabled && 'opacity-50 cursor-not-allowed'
          )}
        >
          <span
            className={cn(
              'flex items-center justify-center w-8 h-8 shrink-0 rounded-md border-2 border-border overflow-hidden'
            )}
          >
            {value ? (
              <span
                className="w-full h-full"
                style={{ backgroundColor: normalizedValue.startsWith('#') ? normalizedValue : `#${normalizedValue}` }}
              />
            ) : (
              <span
                className="w-full h-full bg-muted"
                style={{
                  backgroundImage:
                    'repeating-conic-gradient(#ccc 0% 25%, transparent 0% 50%) 50% / 6px 6px',
                }}
                aria-hidden
              />
            )}
          </span>
          <span className="flex-1 text-sm text-muted-foreground">
            {value ? (isPreset ? value : 'Custom') : 'Select color'}
          </span>
          <ChevronDown className="w-4 h-4 shrink-0 text-muted-foreground" />
        </button>
      </PopoverTrigger>
      <PopoverContent
        className="w-auto max-w-[min(280px,calc(100vw-2rem)] max-h-[min(320px,70vh)] overflow-hidden flex flex-col p-3 rounded-lg border border-border shadow-lg"
        align="start"
        sideOffset={6}
        avoidCollisions={true}
        collisionPadding={12}
      >
        <div className="grid grid-cols-6 sm:grid-cols-7 gap-1.5 max-h-40 overflow-y-auto">
          {allowClear && (
            <button
              type="button"
              onClick={() => handleSelect('')}
              title="No color"
              className={cn(
                'flex flex-col items-center justify-center gap-0.5 min-w-[2.25rem] min-h-[2.25rem] rounded-md border-2 shrink-0 transition-all bg-background',
                !value
                  ? 'border-primary ring-2 ring-primary/20'
                  : 'border-border hover:border-muted-foreground/40 hover:bg-muted/50'
              )}
            >
              <span
                className="w-4 h-4 rounded-sm border border-border bg-muted shrink-0"
                style={{
                  backgroundImage:
                    'repeating-conic-gradient(#ccc 0% 25%, transparent 0% 50%) 50% / 6px 6px',
                }}
                aria-hidden
              />
              <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                None
              </span>
            </button>
          )}
          {PRESET_COLORS.map((hex) => {
            const isSelected = normalizedValue === hex.toLowerCase()
            return (
              <button
                key={hex}
                type="button"
                onClick={() => handleSelect(hex)}
                title={hex}
                className={cn(
                  'min-w-[2.25rem] min-h-[2.25rem] rounded-md border-2 shrink-0 transition-all',
                  isSelected
                    ? 'border-primary ring-2 ring-primary/20'
                    : 'border-transparent hover:border-muted-foreground/30 hover:ring-2 hover:ring-muted-foreground/20'
                )}
                style={{ backgroundColor: hex }}
              />
            )
          })}
        </div>
        <div className="mt-3 pt-3 border-t border-border flex items-center gap-2 shrink-0">
          <span className="text-xs text-muted-foreground shrink-0">Custom</span>
          <input
            type="color"
            value={
              normalizedValue
                ? normalizedValue.startsWith('#')
                  ? normalizedValue
                  : `#${normalizedValue}`
                : '#3b82f6'
            }
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            className="w-9 h-9 rounded-md border border-input cursor-pointer p-0.5 bg-background"
          />
          <input
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            placeholder="#hex"
            className="flex-1 min-w-0 px-2 py-1.5 text-xs font-mono bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
          />
        </div>
      </PopoverContent>
    </Popover>
  )
}
