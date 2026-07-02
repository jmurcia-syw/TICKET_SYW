import type { Permission } from './api'

export interface PermissionRef {
  id: string
  module: string
  action: string
}

export interface RoleDetail {
  id: string
  name: string
  description: string | null
  active: boolean
  permissions: PermissionRef[]
  created_at: string
}

export interface RoleFormData {
  name: string
  description?: string
}

export interface RolePermissionsUpdate {
  permission_ids: string[]
}

export interface PermissionCatalogItem {
  id: string
  module: string
  action: string
  description: string | null
}

export interface PermissionFormData {
  module: string
  action: string
  description?: string
}

export type { Permission }
