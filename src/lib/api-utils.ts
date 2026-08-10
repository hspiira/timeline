export interface ApiFieldError {
  field: string
  message: string
}

export interface ApiErrorDisplay {
  message: string
  code?: string
  fieldErrors?: ApiFieldError[]
}

export function getApiErrorDisplay(
  options: { error: unknown; status?: number },
  defaultMessage = 'An unexpected error occurred'
): ApiErrorDisplay {
  const { error, status } = options
  const obj = typeof error === 'object' && error !== null ? (error as Record<string, unknown>) : null

  if (status === 429) {
    return {
      message: obj && typeof obj.message === 'string' ? obj.message : 'Too many requests; please try again later.',
      code: 'RATE_LIMITED',
    }
  }

  if (status === 422 && obj && Array.isArray(obj.details)) {
    const fieldErrors: ApiFieldError[] = (obj.details as Array<{ loc?: (string | number)[]; msg?: string }>)
      .filter((d) => d && (d.loc || d.msg))
      .map((d) => ({
        field: Array.isArray(d.loc) ? d.loc.filter((x) => typeof x === 'string').join('.') : 'body',
        message: typeof d.msg === 'string' ? d.msg : 'Invalid value',
      }))
    const message =
      fieldErrors.length > 0
        ? fieldErrors.map((e) => (e.field ? `${e.field}: ${e.message}` : e.message)).join('. ')
        : (obj.message as string) || defaultMessage
    return { message, code: 'VALIDATION_ERROR', fieldErrors }
  }

  // Transition violation (409): { error: "TRANSITION_VIOLATION", message: "...", details: { event_type, required_prior_event_types } }
  const code = typeof obj?.error === 'string' ? obj.error : undefined
  const details = obj && typeof obj.details === 'object' && obj.details !== null ? (obj.details as Record<string, unknown>) : null
  const requiredPrior = details && Array.isArray(details.required_prior_event_types) ? (details.required_prior_event_types as string[]) : null
  if (code === 'TRANSITION_VIOLATION') {
    const message =
      typeof obj?.message === 'string'
        ? obj.message
        : requiredPrior && requiredPrior.length > 0
          ? `This event type cannot be created yet. Required prior event types: ${requiredPrior.join(', ')}.`
          : 'This event type cannot be created yet; required prior events are missing.'
    return { message, code: 'TRANSITION_VIOLATION' }
  }

  // Schema validation error: { error: "SCHEMA_VALIDATION_ERROR", message: "...", details: { schema_type, errors: [] } }
  const detailsErrors = details && Array.isArray(details.errors) ? details.errors : []
  if (code === 'SCHEMA_VALIDATION_ERROR' && detailsErrors.length > 0) {
    const fieldErrors: ApiFieldError[] = detailsErrors
      .map((e: unknown) => {
        if (typeof e === 'string') return { field: 'payload', message: e }
        if (e && typeof e === 'object' && 'message' in e) {
          const msg = (e as { message?: string }).message
          const path = (e as { path?: string | string[] }).path
          const field = path
            ? Array.isArray(path)
              ? path.join('.')
              : String(path)
            : 'payload'
          return { field, message: typeof msg === 'string' ? msg : 'Validation failed' }
        }
        return null
      })
      .filter((e): e is ApiFieldError => e !== null)
    const baseMessage = typeof obj?.message === 'string' ? obj.message : defaultMessage
    const schemaType = details && typeof details.schema_type === 'string' ? details.schema_type : undefined
    const message =
      fieldErrors.length > 0
        ? [baseMessage, ...fieldErrors.map((e) => (e.field ? `${e.field}: ${e.message}` : e.message))].join(' — ')
        : baseMessage + (schemaType ? ` (${schemaType})` : '')
    return { message, code, fieldErrors }
  }

  if (obj && typeof obj.message === 'string') {
    return {
      message: obj.message,
      code: typeof obj.error === 'string' ? obj.error : undefined,
    }
  }
  if (obj && typeof obj.detail === 'string') {
    return {
      message: obj.detail,
      code: typeof obj.error === 'string' ? obj.error : undefined,
    }
  }
  if (obj && Array.isArray(obj.detail)) {
    const parts = (obj.detail as Array<{ loc?: string[]; msg?: string }>).map(
      (d) => (d.msg ?? (Array.isArray(d.loc) ? d.loc.join('.') : ''))
    )
    return {
      message: parts.filter(Boolean).join('. ') || defaultMessage,
      code: 'VALIDATION_ERROR',
    }
  }

  return { message: defaultMessage }
}

export function isAuthOrPermissionError(display: ApiErrorDisplay, status?: number): boolean {
  if (status === 401 || status === 403) return true
  const c = display.code?.toUpperCase()
  return (
    c === 'PERMISSION_DENIED' ||
    c === 'AUTHORIZATION_ERROR' ||
    c === 'AUTHENTICATION_ERROR'
  )
}

export function getApiErrorMessage(error: unknown, defaultMessage = 'An unexpected error occurred'): string {
  return getApiErrorDisplay({ error }, defaultMessage).message
} 