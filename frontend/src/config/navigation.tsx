import type { ReactNode } from 'react'
import { TeamOutlined, ProjectOutlined, UserOutlined, StarOutlined, DatabaseOutlined, SafetyCertificateOutlined, FileTextOutlined, DashboardOutlined, TagsOutlined, AppstoreOutlined, ClockCircleOutlined, BarChartOutlined, UnorderedListOutlined, FieldTimeOutlined, CalendarOutlined } from '@ant-design/icons'
import type { Permission } from '../types/api'

export interface NavLeaf {
  key: string
  icon: ReactNode
  label: string
  module: string
  /** Acción de permiso requerida para mostrar este ítem (default: 'view'). Puede ser una
   * lista — cualquiera de ellas habilita el ítem (ej. Tickets: 'view' o 'view_own'). */
  action?: string | string[]
}

export const MAESTROS_GROUP_KEY = 'maestros'

export const maestrosGroupIcon = <DatabaseOutlined />

export const maestrosNavItems: NavLeaf[] = [
  { key: '/clients', icon: <TeamOutlined />, label: 'Clientes', module: 'clients' },
  { key: '/projects', icon: <ProjectOutlined />, label: 'Proyectos', module: 'projects' },
  { key: '/team', icon: <UserOutlined />, label: 'Equipo', module: 'resources' },
  { key: '/skills', icon: <StarOutlined />, label: 'Skills', module: 'skills' },
  { key: '/roles', icon: <SafetyCertificateOutlined />, label: 'Roles y Permisos', module: 'roles' },
  { key: '/client-contacts', icon: <UserOutlined />, label: 'Usuarios/cliente', module: 'client_contacts', action: 'manage' },
  { key: '/sla-rules', icon: <FieldTimeOutlined />, label: 'SLA', module: 'sla_rules', action: 'manage' },
  { key: '/catalogs', icon: <TagsOutlined />, label: 'Catálogos', module: 'catalogs' },
]

/** Ítems de la Fase 1 — Tickets (van al nivel raíz del menú, antes de Maestros). */
export const ticketsNavItems: NavLeaf[] = [
  { key: '/tickets', icon: <FileTextOutlined />, label: 'Tickets', module: 'tickets', action: ['view', 'view_own'] },
  { key: '/my-tasks', icon: <UnorderedListOutlined />, label: 'Mis Tareas', module: 'tickets', action: ['view', 'view_own'] },
  { key: '/kanban', icon: <AppstoreOutlined />, label: 'Kanban', module: 'tickets' },
  { key: '/assignment-panel', icon: <DashboardOutlined />, label: 'Panel de Asignación', module: 'assignment_panel' },
]

/** Ítems de la Fase 2 — Registro de tiempos (van junto a los de Tickets). */
export const workSessionsNavItems: NavLeaf[] = [
  { key: '/registro-tiempos', icon: <ClockCircleOutlined />, label: 'Registro de Tiempos', module: 'work_sessions' },
  { key: '/reporte-tiempos', icon: <BarChartOutlined />, label: 'Reporte de Tiempos', module: 'work_sessions' },
]

function hasNavAccess(permissions: Permission[], item: NavLeaf): boolean {
  const actions = Array.isArray(item.action) ? item.action : [item.action ?? 'view']
  return permissions.some(p => p.module === item.module && actions.includes(p.action))
}

/** Filtra los items de navegación por los permisos que tiene el usuario autenticado
 * (por defecto `view`; algunos ítems aceptan una lista de acciones alternativas). */
export function getVisibleNavItems(permissions: Permission[]): NavLeaf[] {
  return maestrosNavItems.filter(item => hasNavAccess(permissions, item))
}

export function getVisibleTicketNavItems(permissions: Permission[]): NavLeaf[] {
  return ticketsNavItems.filter(item => hasNavAccess(permissions, item))
}

/** work_sessions no usa la acción 'view' — cualquier permiso del módulo (view_own incluido,
 * que todos los roles internos tienen) habilita ver estas pantallas. */
export function getVisibleWorkSessionNavItems(permissions: Permission[]): NavLeaf[] {
  return workSessionsNavItems.filter(item =>
    permissions.some(p => p.module === item.module)
  )
}

/** Ítems de la Fase 5 (spec 020, Historia 2) — vacaciones y permisos. `create` lo tiene
 * cualquier rol interno vinculado a un Recurso (no `Encargado`, contacto externo). */
export const absenceNavItems: NavLeaf[] = [
  { key: '/absence-requests', icon: <CalendarOutlined />, label: 'Vacaciones y Permisos', module: 'absence_requests', action: 'create' },
  { key: '/calendar', icon: <CalendarOutlined />, label: 'Calendarios', module: 'resources', action: 'view' },
]

export function getVisibleAbsenceNavItems(permissions: Permission[]): NavLeaf[] {
  return absenceNavItems.filter(item => hasNavAccess(permissions, item))
}
