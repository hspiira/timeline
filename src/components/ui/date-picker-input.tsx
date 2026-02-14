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

function formatDate(date: Date | undefined): string {
  if (!date) return ''
  return date.toLocaleDateString('en-US', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  })
}

function isValidDate(date: Date | undefined): boolean {
  if (!date) return false
  return !Number.isNaN(date.getTime())
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
    const parsed = new Date(raw)
    if (isValidDate(parsed)) {
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

  return (
    <FormField label={label} required={required} hint={hint}>
      <div className={cn('flex gap-1', className)}>
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
          className="rounded-none border-r-0"
        />
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <Button
              type="button"
              variant="outline"
              size="icon"
              disabled={disabled}
              className="rounded-none border-l border-input shrink-0"
              aria-label="Select date"
            >
              <CalendarIcon className="size-4" />
            </Button>
          </PopoverTrigger>
          <PopoverContent
            className="w-auto overflow-hidden p-0"
            align="end"
            alignOffset={-8}
            sideOffset={8}
          >
            <Calendar
              mode="single"
              selected={date}
              month={month}
              onMonthChange={setMonth}
              onSelect={handleSelect}
            />
          </PopoverContent>
        </Popover>
      </div>
    </FormField>
  )
}
