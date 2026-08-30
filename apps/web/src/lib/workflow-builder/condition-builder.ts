/**
 * Condition builder – compile simple (field, operator, value) to expression string
 * for non-technical users. Backend still receives and evaluates the expression.
 */

export const CONDITION_OPERATORS = [
  { value: 'not_empty', label: 'is not empty' },
  { value: 'empty', label: 'is empty' },
  { value: 'eq', label: 'equals' },
  { value: 'neq', label: 'is not equal to' },
  { value: 'gt', label: 'is greater than' },
  { value: 'gte', label: 'is at least' },
  { value: 'lt', label: 'is less than' },
  { value: 'lte', label: 'is at most' },
  { value: 'contains', label: 'contains' },
] as const

export type ConditionOperator = (typeof CONDITION_OPERATORS)[number]['value']

/** Build expression from simple rule. Field is the payload key (e.g. "amount"). */
export function simpleConditionToExpression(
  field: string,
  operator: ConditionOperator,
  value: string,
): string {
  const key = field.trim()
  if (!key) return ''
  const path = `payload.${key}`
  const safePath = /^payload\.\w+(\.\w+)*$/.test(path)
    ? path
    : `payload['${key.replace(/'/g, "\\'")}']`

  switch (operator) {
    case 'empty':
      return `!${safePath}`
    case 'not_empty':
      return `!!${safePath}`
    case 'eq':
      return numberOrStringExpr(safePath, value, '===')
    case 'neq':
      return numberOrStringExpr(safePath, value, '!==')
    case 'gt':
      return `${safePath} > ${numberOrRaw(value)}`
    case 'gte':
      return `${safePath} >= ${numberOrRaw(value)}`
    case 'lt':
      return `${safePath} < ${numberOrRaw(value)}`
    case 'lte':
      return `${safePath} <= ${numberOrRaw(value)}`
    case 'contains':
      return value.trim()
        ? `(${safePath} != null && String(${safePath}).includes(${JSON.stringify(value)}))`
        : `!!${safePath}`
    default:
      return ''
  }
}

function numberOrRaw(v: string): string {
  const t = v.trim()
  if (t === '') return '0'
  const n = Number(t)
  if (!Number.isNaN(n)) return String(n)
  return JSON.stringify(t)
}

function numberOrStringExpr(path: string, value: string, op: '===' | '!=='): string {
  const t = value.trim()
  if (t === '') return `${path} ${op} ''`
  const n = Number(t)
  if (!Number.isNaN(n)) return `${path} ${op} ${n}`
  return `${path} ${op} ${JSON.stringify(t)}`
}

/** Best-effort parse expression back to simple parts for the builder. */
export function parseSimpleCondition(expression: string): {
  field: string
  operator: ConditionOperator
  value: string
} | null {
  const e = expression.trim()
  if (!e) return null

  const notEmptyMatch = e.match(/^!!(payload\.\w+(\.\w+)*)$/)
  if (notEmptyMatch) {
    return {
      field: notEmptyMatch[1].replace(/^payload\./, ''),
      operator: 'not_empty',
      value: '',
    }
  }

  const emptyMatch = e.match(/^!(payload\.\w+(\.\w+)*)$/)
  if (emptyMatch) {
    return {
      field: emptyMatch[1].replace(/^payload\./, ''),
      operator: 'empty',
      value: '',
    }
  }

  const eqMatch =
    e.match(/^(payload\.\w+(\.\w+)*)\s*===\s*(.+)$/) ||
    e.match(/^(payload\.\w+(\.\w+)*)\s*==\s*(.+)$/)
  if (eqMatch) {
    const val = tryUnquote(eqMatch[3])
    return { field: eqMatch[1].replace(/^payload\./, ''), operator: 'eq', value: val }
  }

  const neqMatch =
    e.match(/^(payload\.\w+(\.\w+)*)\s*!==\s*(.+)$/) ||
    e.match(/^(payload\.\w+(\.\w+)*)\s*!=\s*(.+)$/)
  if (neqMatch) {
    const val = tryUnquote(neqMatch[3])
    return { field: neqMatch[1].replace(/^payload\./, ''), operator: 'neq', value: val }
  }

  const gtMatch = e.match(/^(payload\.\w+(\.\w+)*)\s*>\s*(.+)$/)
  if (gtMatch)
    return { field: gtMatch[1].replace(/^payload\./, ''), operator: 'gt', value: gtMatch[3].trim() }

  const gteMatch = e.match(/^(payload\.\w+(\.\w+)*)\s*>=\s*(.+)$/)
  if (gteMatch)
    return {
      field: gteMatch[1].replace(/^payload\./, ''),
      operator: 'gte',
      value: gteMatch[3].trim(),
    }

  const ltMatch = e.match(/^(payload\.\w+(\.\w+)*)\s*<\s*(.+)$/)
  if (ltMatch)
    return { field: ltMatch[1].replace(/^payload\./, ''), operator: 'lt', value: ltMatch[3].trim() }

  const lteMatch = e.match(/^(payload\.\w+(\.\w+)*)\s*<=\s*(.+)$/)
  if (lteMatch)
    return {
      field: lteMatch[1].replace(/^payload\./, ''),
      operator: 'lte',
      value: lteMatch[3].trim(),
    }

  return null
}

function tryUnquote(s: string): string {
  const t = s.trim()
  if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'"))) {
    try {
      return JSON.parse(t.replace(/'/g, '"'))
    } catch {
      return t.slice(1, -1)
    }
  }
  return t
}

/** Validate condition expression (same evaluation as execution engine). Returns user-facing error if invalid. */
export function validateConditionExpression(
  expression: string,
): { valid: true } | { valid: false; error: string } {
  const e = expression.trim()
  if (!e) return { valid: true }
  try {
    const fn = new Function('payload', `return Boolean(${e})`)
    fn({})
    return { valid: true }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return {
      valid: false,
      error: message.length > 80 ? `${message.slice(0, 77)}…` : message,
    }
  }
}
