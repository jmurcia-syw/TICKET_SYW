import type { ReactNode } from 'react'
import { TeamOutlined, ProjectOutlined, UserOutlined, SettingOutlined, StarOutlined, DatabaseOutlined } from '@ant-design/icons'
import type { Role } from '../types/api'

export interface NavLeaf {
  key: string
  icon: ReactNode
  label: string
  roles: Role[]
}

export const MAESTROS_GROUP_KEY = 'maestros'

export const maestrosGroupIcon = <DatabaseOutlined />

export const maestrosNavItems: NavLeaf[] = [
  { key: '/clients', icon: <TeamOutlined />, label: 'Clientes', roles: ['admin', 'coordinator'] },
  { key: '/projects', icon: <ProjectOutlined />, label: 'Proyectos', roles: ['admin', 'coordinator'] },
  { key: '/resources', icon: <UserOutlined />, label: 'Recursos', roles: ['admin', 'coordinator', 'qm', 'resolver'] },
  { key: '/skills', icon: <StarOutlined />, label: 'Skills', roles: ['admin', 'coordinator', 'qm', 'resolver'] },
  { key: '/users', icon: <SettingOutlined />, label: 'Usuarios', roles: ['admin'] },
]
