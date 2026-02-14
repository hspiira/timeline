/**
 * Shared date/time formatting. UK locale (en-GB): dates as dd/mm/yyyy.
 * Use these instead of inline toLocaleDateString/toLocaleTimeString.
 */

const locale = 'en-GB'

/** UK date: dd/mm/yyyy */
const dateOptions: Intl.DateTimeFormatOptions = {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
}

const timeOptions: Intl.DateTimeFormatOptions = {
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
}

const dateTimeOptions: Intl.DateTimeFormatOptions = {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
}

/** UK short date: dd/mm (no year, for compact lists) */
const shortDateOptions: Intl.DateTimeFormatOptions = {
  day: '2-digit',
  month: '2-digit',
}

/** e.g. "14/02/2025" (UK dd/mm/yyyy) */
export function formatEventDate(date: Date | string): string {
  return new Date(date).toLocaleDateString(locale, dateOptions)
}

/** e.g. "14:30" (24-hour UK) */
export function formatEventTime(date: Date | string): string {
  return new Date(date).toLocaleTimeString(locale, timeOptions)
}

/** e.g. "14/02/2025, 14:30" (UK dd/mm/yyyy and 24h) */
export function formatEventDateTime(date: Date | string): string {
  return new Date(date).toLocaleString(locale, dateTimeOptions)
}

/** e.g. "14/02" (compact UK) */
export function formatShortDate(date: Date | string): string {
  return new Date(date).toLocaleDateString(locale, shortDateOptions)
}

/** Full UK locale string (dd/mm/yyyy, 24h time) */
export function formatFullDateTime(date: Date | string): string {
  return new Date(date).toLocaleString(locale, dateTimeOptions)
}
