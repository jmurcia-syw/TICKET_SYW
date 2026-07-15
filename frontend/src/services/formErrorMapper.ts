import type { FormInstance } from 'antd'
import type { AxiosError } from 'axios'
import type { ApiErrorBody } from './errorNotifier'

/** OBS-0018: regla que asocia un código de error de la API a un campo de formulario.
 * `messageIncludes` distingue campos distintos que comparten un código genérico
 * (ej. "validation_error" puede ser sobre `name` o sobre `contact_phone`). */
export interface FieldErrorRule {
  code: string
  field: string
  messageIncludes?: string[]
}

/**
 * Pinta el error de la API junto al campo del formulario (`form.setFields`) en vez de dejar
 * que se pierda en un toast fugaz. Devuelve `true` si pudo asociar el error a un campo
 * conocido (el llamador puede evitar mostrar también un mensaje genérico en ese caso).
 * El toast global (`errorNotifier`, ya conectado en el interceptor de `apiClient`) sigue
 * mostrándose de todas formas para errores sin campo asociado (403, 500, red).
 */
export function mapApiErrorToFormFields(err: unknown, form: FormInstance, rules: FieldErrorRule[]): boolean {
  const axiosErr = err as AxiosError<Partial<ApiErrorBody>>
  const data = axiosErr.response?.data
  const message = data?.message
  if (!message) return false
  const code = (data?.code ?? data?.error ?? '').toLowerCase()
  const rule = rules.find(r =>
    r.code.toLowerCase() === code &&
    (!r.messageIncludes || r.messageIncludes.some(kw => message.includes(kw)))
  )
  if (!rule) return false
  form.setFields([{ name: rule.field, errors: [message] }])
  return true
}
