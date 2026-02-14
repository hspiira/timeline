/**
 * Shared date/time formatting. Use these instead of inline toLocaleDateString/toLocaleTimeString
 * so locale and options stay consistent across the app.
 */

const locale = 'en-US'

const dateOptions: Intl.DateTimeFormatOptions = {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
}

const timeOptions: Intl.DateTimeFormatOptions = {
  hour: '2-digit',
  minute: '2-digit',
}

const dateTimeOptions: Intl.DateTimeFormatOptions = {
  month: 'short',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
}

const shortDateOptions: Intl.DateTimeFormatOptions = {
  month: 'short',
  day: 'numeric',
}

/** e.g. "Feb 14, 2025" */
export function formatEventDate(date: Date | string): string {
  return new Date(date).toLocaleDateString(locale, dateOptions)
}

/** e.g. "2:30 PM" */
export function formatEventTime(date: Date | string): string {
  return new Date(date).toLocaleTimeString(locale, timeOptions)
}

/** e.g. "Feb 14, 2:30 PM" */
export function formatEventDateTime(date: Date | string): string {
  return new Date(date).toLocaleString(locale, dateTimeOptions)
}

/** e.g. "Feb 14" (for compact lists) */
export function formatShortDate(date: Date | string): string {
  return new Date(date).toLocaleDateString(locale, shortDateOptions)
}

/** Full locale string (e.g. for verify/email screens) */
export function formatFullDateTime(date: Date | string): string {
  return new Date(date).toLocaleString(locale)
}
