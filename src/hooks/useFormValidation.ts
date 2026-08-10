import { useState, useCallback } from 'react'

export interface ValidationRules {
  [fieldName: string]: {
    required?: boolean | string
    minLength?: { value: number; message: string }
    maxLength?: { value: number; message: string }
    pattern?: { value: RegExp; message: string }
    custom?: (value: any) => string | null
  }
}

export interface FormErrors {
  [fieldName: string]: string | null
}

export function useFormValidation(rules: ValidationRules) {
  const [errors, setErrors] = useState<FormErrors>({})

  const validateField = useCallback(
    (fieldName: string, value: any): string | null => {
      const fieldRules = rules[fieldName]
      if (!fieldRules) return null

      // Required validation
      if (fieldRules.required) {
        if (!value || (typeof value === 'string' && value.trim() === '')) {
          return typeof fieldRules.required === 'string'
            ? fieldRules.required
            : 'This field is required'
        }
      }

      // Skip other validations if value is empty (unless required)
      if (!value || (typeof value === 'string' && value.trim() === '')) {
        return null
      }

      // Min length validation
      if (
        fieldRules.minLength &&
        value.length < fieldRules.minLength.value
      ) {
        return fieldRules.minLength.message
      }

      // Max length validation
      if (
        fieldRules.maxLength &&
        value.length > fieldRules.maxLength.value
      ) {
        return fieldRules.maxLength.message
      }

      // Pattern validation
      if (fieldRules.pattern && !fieldRules.pattern.value.test(value)) {
        return fieldRules.pattern.message
      }

      // Custom validation
      if (fieldRules.custom) {
        return fieldRules.custom(value)
      }

      return null
    },
    [rules]
  )

  const validateForm = useCallback(
    (values: Record<string, any>): boolean => {
      const newErrors: FormErrors = {}
      let hasErrors = false

      Object.keys(rules).forEach((fieldName) => {
        const error = validateField(fieldName, values[fieldName])
        if (error) {
          newErrors[fieldName] = error
          hasErrors = true
        } else {
          newErrors[fieldName] = null
        }
      })

      setErrors(newErrors)
      return !hasErrors
    },
    [rules, validateField]
  )

  const setFieldError = useCallback((fieldName: string, error: string | null) => {
    setErrors((prev) => ({
      ...prev,
      [fieldName]: error,
    }))
  }, [])

  const clearErrors = useCallback(() => {
    setErrors({})
  }, [])

  return {
    errors,
    validateField,
    validateForm,
    setFieldError,
    clearErrors,
  }
}
