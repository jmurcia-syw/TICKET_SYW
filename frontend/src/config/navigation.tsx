import type { ReactNode } from 'react'
import { TeamOutlined, ProjectOutlined, UserOutlined, StarOutlined, DatabaseOutlined, SafetyCertificateOutlined, FileTextOutlined, DashboardOutlined, TagsOutlined, AppstoreOutlined } from '@ant-design/icons'
import type { Permission } from '../types/api'

export interface NavLeaf {
  key: string
  icon: ReactNode
  label: string
  module: string
}

export const MAESTROS_GROUP_KEY = 'maestros'

export const maestrosGroupIcon = <DatabaseOutlined />

export const maestrosNavItems: NavLeaf[] = [
  { key: '/clients', icon: <TeamOutlined />, label: 'Clientes', module: 'clients' },
  { key: '/projects', icon: <ProjectOutlined />, label: 'Proyectos', module: 'projects' },
  { key: '/team', icon: <UserOutlined />, label: 'Equipo', module: 'resources' },
  { key: '/skills', icon: <StarOutlined />, label: 'Skills', module: 'skills' },
  { key: '/roles', icon: <SafetyCertificateOutlined />, label: 'Roles y Permisos', module: 'roles' },
]

/** Ítems de la Fase 1 — Tickets (van al nivel raíz del menú, antes de Maestros). */
export const ticketsNavItems: NavLeaf[] = [
  { key: '/tickets', icon: <FileTextOutlined />, label: 'Tickets', module: 'tickets' },
  { key: '/kanban', icon: <AppstoreOutlined />, label: 'Kanban', module: 'tickets' },
  { key: '/assignment-panel', icon: <DashboardOutlined />, label: 'Panel de Asignación', module: 'assignment_panel' },
  { key: '/catalogs', icon: <TagsOutlined />, label: 'Catálogos', module: 'catalogs' },
]

/** Filtra los items de navegación por los permisos `view` que tiene el usuario autenticado. */
export function getVisibleNavItems(permissions: Permission[]): NavLeaf[] {
  return maestrosNavItems.filter(item =>
    permissions.some(p => p.module === item.module && p.action === 'view')
  )
}

export function getVisibleTicketNavItems(permissions: Permission[]): NavLeaf[] {
  return ticketsNavItems.filter(item =>
    permissions.some(p => p.module === item.module && p.action === 'view')
  )
}
