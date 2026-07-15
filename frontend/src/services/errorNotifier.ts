import { message as staticMessage } from 'antd'
import type { MessageInstance } from 'antd/es/message/interface'
import type { AxiosError } from 'axios'

/** Contrato estándar de error de la API (specs/013, contracts/error-contract.md). */
export interface ApiErrorBody {
  success: false
  message: string
  code: string
  /** Código snake_case legado; deprecado, no usar en código nuevo. */
  error?: string
}

export const GENERIC_ERROR_MESSAGE =
  'Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo'

const DEDUPE_WINDOW_MS = 3000
const lastShownAt = new Map<string, number>()

// Instancia de mensajes ligada al <App> de antd para respetar tema/locale;
// la estática es el fallback hasta que App.tsx llama a bindMessageApi.
let messageApi: MessageInstance = staticMessage

export function bindMessageApi(api: MessageInstance): void {
  messageApi = api
}

function extractMessage(error: AxiosError<Partial<ApiErrorBody>>): string {
  const serverMessage = error.response?.data?.message
  if (typeof serverMessage === 'string' && serverMessage.trim() !== '') {
    return serverMessage
  }
  return GENERIC_ERROR_MESSAGE
}

/**
 * Muestra un toast de error con el mensaje del servidor o el genérico.
 * Mensajes idénticos dentro de la ventana de dedupe se muestran una sola vez.
 */
export function notifyApiError(error: AxiosError<Partial<ApiErrorBody>>): void {
  const text = extractMessage(error)
  const now = Date.now()
  const last = lastShownAt.get(text)
  if (last !== undefined && now - last < DEDUPE_WINDOW_MS) {
    return
  }
  lastShownAt.set(text, now)
  void messageApi.error(text)
}
