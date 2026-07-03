import type { CommentType, TicketStatus } from '../types/ticket'

/**
 * Espejo (solo lectura) de la matriz FSM del backend (backend/domain/fsm/ticket_fsm.py)
 * — únicamente para las 8 columnas activas del Kanban. Determina qué acción disparar
 * cuando el usuario arrastra una tarjeta de una columna a otra. La validación real y
 * definitiva sigue viviendo en el backend; esto solo decide qué diálogo abrir.
 */
export type KanbanTransition =
  | { kind: 'testing'; direction: 'enter' | 'exit' }
  | { kind: 'comment'; commentType: CommentType }
  | { kind: 'assign'; mode: 'resolver' | 'pre_analysis' }
  | { kind: 'resolution' }

const MATRIX: Record<string, KanbanTransition> = {
  'nuevo->contacto': { kind: 'assign', mode: 'resolver' },
  'nuevo->pre_analisis': { kind: 'assign', mode: 'pre_analysis' },
  'pre_analisis->contacto': { kind: 'assign', mode: 'resolver' },
  'pre_analisis->pendiente_usuario': { kind: 'comment', commentType: 'solicitud_informacion' },
  'contacto->en_analisis': { kind: 'comment', commentType: 'confirmacion_atencion' },
  'en_analisis->en_ejecucion': { kind: 'comment', commentType: 'termina_analisis' },
  'en_analisis->pendiente_usuario': { kind: 'comment', commentType: 'solicitud_informacion' },
  'en_ejecucion->pendiente_usuario': { kind: 'comment', commentType: 'solicitud_informacion' },
  'en_ejecucion->resuelto': { kind: 'comment', commentType: 'solicitud_cierre' },
  'en_ejecucion->en_pruebas': { kind: 'testing', direction: 'enter' },
  'en_pruebas->en_ejecucion': { kind: 'testing', direction: 'exit' },
  'en_pruebas->resuelto': { kind: 'comment', commentType: 'solicitud_cierre' },
  'pendiente_usuario->en_ejecucion': { kind: 'comment', commentType: 'respuesta_usuario' },
  'resuelto->en_ejecucion': { kind: 'resolution' },
}

export function getKanbanTransition(from: TicketStatus, to: TicketStatus): KanbanTransition | null {
  if (from === to) return null
  return MATRIX[`${from}->${to}`] ?? null
}

/** Columnas destino alcanzables directamente desde un estado — para el mensaje de error. */
export function reachableFrom(from: TicketStatus): TicketStatus[] {
  return Object.keys(MATRIX)
    .filter(key => key.startsWith(`${from}->`))
    .map(key => key.split('->')[1] as TicketStatus)
}
