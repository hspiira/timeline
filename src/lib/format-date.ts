/**
 * Shared date/time formatting for UI. Backend returns ISO 8601 strings (event_time, created_at, timestamp, etc.).
 * Use these instead of inline toLocaleDateString/toLocaleTimeString for consistent UK (en-GB) rendering.
 */

const locale = 'en-GB'

/** Parse ISO or return invalid Date; use with format* for display. */
function parseDate(value: Date | string | null | undefined): Date {
  if (value instanceof Date) return value
  if (value == null || String(value).trim() === '') return new Date(NaN)
  return new Date(value)
}

/** Format for display, or return fallback for invalid/empty (e.g. "—"). */
function formatOrFallback(
  value: Date | string | null | undefined,
  formatter: (d: Date) => string,
  fallback = '—',
): string {
  const d = parseDate(value)
  if (Number.isNaN(d.getTime())) return fallback
  return formatter(d)
}

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

const timeWithSecondsOptions: Intl.DateTimeFormatOptions = {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
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

/** e.g. "14:30:45" (24-hour UK with seconds, for timeline) */
export function formatEventTimeWithSeconds(date: Date | string): string {
  return new Date(date).toLocaleTimeString(locale, timeWithSecondsOptions)
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

/** Format datetime for display; returns fallback for invalid/empty. Use in tables and optional fields. */
export function formatDateTimeSafe(
  value: Date | string | null | undefined,
  fallback = '—',
): string {
  return formatOrFallback(value, (d) => d.toLocaleString(locale, dateTimeOptions), fallback)
}

/** Format date only; returns fallback for invalid/empty. */
export function formatDateSafe(value: Date | string | null | undefined, fallback = '—'): string {
  return formatOrFallback(value, (d) => d.toLocaleDateString(locale, dateOptions), fallback)
}
