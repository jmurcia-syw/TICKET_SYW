import { useEffect, useState } from 'react'
import { Checkbox, Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { PermissionCatalogItem, RoleDetail } from '../../types/role'
import { palette } from '../../theme'

const ACTION_LABELS: Record<string, string> = {
  view: 'Ver', create: 'Crear', edit: 'Editar', deactivate: 'Desactivar',
  assign: 'Asignar', cancel: 'Cancelar', transition: 'Transicionar', manage: 'Gestionar',
  manage_all: 'Gestionar (todas)', view_all: 'Ver (todas)', view_own: 'Ver (propias)',
}
const actionLabel = (action: string) => ACTION_LABELS[action] ?? action

interface ModuleRow {
  module: string
  byAction: Record<string, PermissionCatalogItem | undefined>
}

interface Props {
  role: RoleDetail
  allPermissions: PermissionCatalogItem[]
  onChange: (permissionIds: string[]) => void
}

export default function PermissionMatrix({ role, allPermissions, onChange }: Props) {
  const [selected, setSelected] = useState<Set<string>>(new Set(role.permissions.map(p => p.id)))

  useEffect(() => {
    setSelected(new Set(role.permissions.map(p => p.id)))
  }, [role.id])

  useEffect(() => {
    onChange(Array.from(selected))
  }, [selected])

  const modules = Array.from(new Set(allPermissions.map(p => p.module))).sort()
  const ACTIONS = Array.from(new Set(allPermissions.map(p => p.action))).sort()
  const rows: ModuleRow[] = modules.map(module => ({
    module,
    byAction: Object.fromEntries(ACTIONS.map(action => [action, allPermissions.find(p => p.module === module && p.action === action)])),
  }))

  const toggle = (permissionId: string | undefined) => {
    if (!permissionId) return
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(permissionId)) next.delete(permissionId)
      else next.add(permissionId)
      return next
    })
  }

  const columns: ColumnsType<ModuleRow> = [
    {
      title: 'Módulo',
      dataIndex: 'module',
      fixed: 'left',
      width: 160,
      render: (m: string) => <strong>{m}</strong>,
      onCell: () => ({ style: { background: palette.slate50 } }),
    },
    ...ACTIONS.map(action => ({
      title: actionLabel(action),
      key: action,
      align: 'center' as const,
      width: 96,
      render: (_: unknown, row: ModuleRow) => {
        const perm = row.byAction[action]
        if (!perm) return <span style={{ color: palette.slate300 }}>—</span>
        return <Checkbox checked={selected.has(perm.id)} onChange={() => toggle(perm.id)} />
      },
      onCell: (row: ModuleRow) => {
        const perm = row.byAction[action]
        if (!perm) return {}
        return { style: { cursor: 'pointer' }, onClick: () => toggle(perm.id) }
      },
    })),
  ]

  return (
    <Table
      rowKey="module"
      columns={columns}
      dataSource={rows}
      pagination={false}
      size="small"
      scroll={{ x: 'max-content' }}
    />
  )
}
