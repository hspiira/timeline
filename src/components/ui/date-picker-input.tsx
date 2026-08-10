'use client'

import * as React from 'react'
import { Calendar } from '@/components/ui/calendar'
import { FormField } from '@/components/ui/FormField'
import { Input } from '@/components/ui/input'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { CalendarIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatEventDate } from '@/lib/format-date'

function isValidDate(date: Date | undefined): boolean {
  if (!date) return false
  return !Number.isNaN(date.getTime())
}

/** Parse dd/mm/yyyy or d/m/yyyy (UK) into Date. */
function parseUKDate(raw: string): Date | null {
  const trimmed = raw.trim()
  if (!trimmed) return null
  const parts = trimmed.split(/[/.-]/)
  if (parts.length === 3) {
    const [d, m, y] = parts.map((p) => parseInt(p, 10))
    if (Number.isNaN(d) || Number.isNaN(m) || Number.isNaN(y)) return null
    const month = m - 1
    const parsed = new Date(y, month, d)
    if (
      parsed.getFullYear() !== y ||
      parsed.getMonth() !== month ||
      parsed.getDate() !== d
    )
      return null
    return parsed
  }
  const fallback = new Date(trimmed)
  return isValidDate(fallback) ? fallback : null
}

/** Format for display in date picker (UK dd/mm/yyyy). */
function formatDate(date: Date | undefined): string {
  if (!date) return ''
  return formatEventDate(date)
}

/** Basic date picker: button trigger + calendar (shadcn Basic leaf). UK dd/mm/yyyy. */
export interface DatePickerProps {
  value?: Date
  onChange?: (date: Date | undefined) => void
  placeholder?: string
  disabled?: boolean
  className?: string
}

export function DatePicker({
  value,
  onChange,
  placeholder = 'Pick a date',
  disabled = false,
  className,
}: DatePickerProps) {
  const [open, setOpen] = React.useState(false)
  const [date, setDate] = React.useState<Date | undefined>(value)
  const [month, setMonth] = React.useState<Date | undefined>(date)

  React.useEffect(() => {
    setDate(value)
    setMonth(value)
  }, [value])

  const handleSelect = (newDate: Date | undefined) => {
    setDate(newDate)
    setOpen(false)
    onChange?.(newDate)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          data-empty={!date}
          className={cn(
            'w-[280px] justify-start text-left font-normal rounded-none',
            !date && 'text-muted-foreground',
            className
          )}
          disabled={disabled}
        >
          <CalendarIcon className="mr-2 size-4 shrink-0" />
          {date ? formatEventDate(date) : <span>{placeholder}</span>}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0 rounded-none" align="start">
        <Calendar
          mode="single"
          selected={date}
          month={month}
          onMonthChange={setMonth}
          onSelect={handleSelect}
        />
      </PopoverContent>
    </Popover>
  )
}

export interface DatePickerInputProps {
  id?: string
  label?: string
  required?: boolean
  hint?: string
  value?: Date
  onChange?: (date: Date | undefined) => void
  placeholder?: string
  disabled?: boolean
  className?: string
}

export function DatePickerInput({
  id,
  label = 'Date',
  required,
  hint,
  value,
  onChange,
  placeholder = 'Pick a date',
  disabled = false,
  className,
}: DatePickerInputProps) {
  const [open, setOpen] = React.useState(false)
  const [date, setDate] = React.useState<Date | undefined>(value)
  const [month, setMonth] = React.useState<Date | undefined>(date)
  const [inputValue, setInputValue] = React.useState(formatDate(date))

  React.useEffect(() => {
    setDate(value)
    setMonth(value)
    setInputValue(formatDate(value))
  }, [value])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value
    setInputValue(raw)
    const parsed = parseUKDate(raw)
    if (parsed) {
      setDate(parsed)
      setMonth(parsed)
      onChange?.(parsed)
    }
  }

  const handleSelect = (newDate: Date | undefined) => {
    setDate(newDate)
    setInputValue(formatDate(newDate))
    setOpen(false)
    onChange?.(newDate)
  }

  // shadcn Input-style date picker: input + popover + calendar (see ui.shadcn.com/docs/components/radix/date-picker)
  return (
    <FormField label={label} required={required} hint={hint}>
      <Popover open={open} onOpenChange={setOpen}>
        <div className={cn('flex gap-0 rounded-none border border-input bg-background', className)}>
          <Input
            id={id}
            value={inputValue}
            placeholder={placeholder}
            onChange={handleInputChange}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') {
                e.preventDefault()
                setOpen(true)
              }
            }}
            disabled={disabled}
            className="rounded-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0"
          />
          <PopoverTrigger asChild>
            <Button
              type="button"
              variant="outline"
              size="icon"
              disabled={disabled}
              className="rounded-none border-0 border-l border-input shrink-0"
              aria-label="Select date"
            >
              <CalendarIcon className="size-4" />
            </Button>
          </PopoverTrigger>
        </div>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            selected={date}
            month={month}
            onMonthChange={setMonth}
            onSelect={handleSelect}
          />
        </PopoverContent>
      </Popover>
    </FormField>
  )
}
