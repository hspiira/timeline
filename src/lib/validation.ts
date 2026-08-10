/**
 * Shared validation helpers. Use instead of duplicating regex and messages.
 */

const ALPHANUMERIC_UNDERSCORE = /^[a-zA-Z0-9_]+$/

/**
 * Validates that a string contains only letters, numbers, and underscores.
 * @param value - String to validate
 * @param fieldName - Display name for error message (e.g. "Event type", "Subject type")
 * @returns Error message or null if valid
 */
export function validateAlphanumericUnderscore(
  value: string,
  fieldName: string
): string | null {
  const trimmed = value.trim()
  if (!trimmed) {
    return `${fieldName} is required`
  }
  if (!ALPHANUMERIC_UNDERSCORE.test(trimmed)) {
    return `${fieldName} must contain only alphanumeric characters and underscores`
  }
  return null
}
