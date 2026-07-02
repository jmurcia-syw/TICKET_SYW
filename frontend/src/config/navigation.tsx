import type { ReactNode } from 'react'
import { TeamOutlined, ProjectOutlined, UserOutlined, SettingOutlined, StarOutlined, DatabaseOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
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
  { key: '/resources', icon: <UserOutlined />, label: 'Recursos', module: 'resources' },
  { key: '/skills', icon: <StarOutlined />, label: 'Skills', module: 'skills' },
  { key: '/users', icon: <SettingOutlined />, label: 'Usuarios', module: 'users' },
  { key: '/roles', icon: <SafetyCertificateOutlined />, label: 'Roles y Permisos', module: 'roles' },
]

/** Filtra los items de navegación por los permisos `view` que tiene el usuario autenticado. */
export function getVisibleNavItems(permissions: Permission[]): NavLeaf[] {
  return maestrosNavItems.filter(item =>
    permissions.some(p => p.module === item.module && p.action === 'view')
  )
}
