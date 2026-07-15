import { useEffect, useState } from 'react'
import { Button, Form, Input, Modal, Space, Table, Tooltip, Typography, message } from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, PlayCircleOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { roleService } from '../services/roleService'
import { permissionService } from '../services/permissionService'
import type { PermissionCatalogItem, RoleDetail, RoleFormData } from '../types/role'
import ConfirmationModal from '../components/common/ConfirmationModal'
import StatusTag from '../components/common/StatusTag'
import PageToolbar from '../components/common/PageToolbar'
import PermissionMatrix from '../components/roles/PermissionMatrix'
import { clientColumnFilter, clientTextColumnFilter } from '../components/common/columnFilters'
import { palette } from '../theme'
import { mapApiErrorToFormFields, type FieldErrorRule } from '../services/formErrorMapper'

// OBS-0018: asocia códigos de error de la API a los campos del formulario de Rol.
const ROLE_ERROR_RULES: FieldErrorRule[] = [
  { code: 'name_duplicate', field: 'name' },
]

export default function RolesPermissionsPage() {
  const [roles, setRoles] = useState<RoleDetail[]>([])
  const [allPermissions, setAllPermissions] = useState<PermissionCatalogItem[]>([])
  const [loading, setLoading] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [editingRole, setEditingRole] = useState<RoleDetail | null>(null)
  const [pendingPermissionIds, setPendingPermissionIds] = useState<string[]>([])
  const [confirmDeactivate, setConfirmDeactivate] = useState<string | null>(null)
  const [form] = Form.useForm<RoleFormData>()

  const load = async () => {
    setLoading(true)
    try {
      const res = await roleService.list({ page_size: 100 })
      setRoles(res.items)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    permissionService.list().then(r => setAllPermissions(r.items))
      .catch(() => message.error('No se pudo cargar el catálogo de permisos'))
  }, [])

  const openCreate = () => {
    form.resetFields()
    setEditingRole(null)
    setPendingPermissionIds([])
    setFormOpen(true)
  }

  const openEdit = (role: RoleDetail) => {
    form.setFieldsValue({ name: role.name, description: role.description ?? undefined })
    setEditingRole(role)
    setPendingPermissionIds(role.permissions.map(p => p.id))
    setFormOpen(true)
  }

  const handleSubmit = async (values: RoleFormData) => {
    try {
      if (editingRole) {
        await roleService.update(editingRole.id, values)
        await roleService.replacePermissions(editingRole.id, pendingPermissionIds)
        message.success('Rol actualizado')
      } else {
        await roleService.create(values)
        message.success('Rol creado. Asígnale permisos editándolo.')
      }
      setFormOpen(false)
      load()
    } catch (err: unknown) {
      if (mapApiErrorToFormFields(err, form, ROLE_ERROR_RULES)) return
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al guardar'
      message.error(msg)
    }
  }

  const handleDeactivate = async (id: string) => {
    try {
      await roleService.deactivate(id)
      message.success('Rol desactivado')
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'No se pudo desactivar el rol'
      message.error(msg)
    } finally {
      setConfirmDeactivate(null)
    }
  }

  const handleActivate = async (id: string) => {
    try {
      await roleService.activate(id)
      message.success('Rol activado')
      load()
    } catch {
      message.error('No se pudo activar el rol')
    }
  }

  const columns: ColumnsType<RoleDetail> = [
    {
      title: 'Nombre', dataIndex: 'name', sorter: (a, b) => a.name.localeCompare(b.name),
      ...clientTextColumnFilter<RoleDetail>('Buscar nombre...', r => r.name),
    },
    { title: 'Descripción', dataIndex: 'description' },
    { title: 'Permisos', dataIndex: 'permissions', render: (p: RoleDetail['permissions']) => p.length },
    {
      title: 'Estado', dataIndex: 'active', render: (v: boolean) => <StatusTag active={v} />,
      ...clientColumnFilter<RoleDetail>(
        [{ text: 'Activo', value: 'true' }, { text: 'Inactivo', value: 'false' }],
        (value, record) => String(record.active) === value,
      ),
    },
    {
      title: 'Acciones', key: 'actions',
      render: (_: unknown, r: RoleDetail) => (
        <Space>
          <Tooltip title="Editar y asignar permisos"><Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} /></Tooltip>
          {r.name !== 'Admin' && (r.active
            ? <Tooltip title="Desactivar"><Button size="small" danger icon={<StopOutlined />} onClick={() => setConfirmDeactivate(r.id)} /></Tooltip>
            : <Tooltip title="Activar"><Button size="small" icon={<PlayCircleOutlined style={{ color: palette.green600 }} />} onClick={() => handleActivate(r.id)} /></Tooltip>)}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageToolbar
        filters={null}
        action={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Nuevo rol</Button>}
      />

      <Table rowKey="id" columns={columns} dataSource={roles} loading={loading} pagination={false} />

      <Modal
        title={editingRole ? `Editar rol — ${editingRole.name}` : 'Nuevo rol'}
        open={formOpen}
        onCancel={() => setFormOpen(false)}
        onOk={() => form.submit()}
        okText="Guardar"
        width={640}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="Nombre" rules={[{ required: true, message: 'El nombre es requerido' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Descripción"><Input.TextArea rows={2} /></Form.Item>
        </Form>
        {editingRole && (
          <>
            <Typography.Paragraph type="secondary" style={{ marginTop: 8 }}>
              Permisos (módulo × acción):
            </Typography.Paragraph>
            <PermissionMatrix role={editingRole} allPermissions={allPermissions} onChange={setPendingPermissionIds} />
          </>
        )}
        {!editingRole && (
          <Typography.Paragraph type="secondary">
            El rol se crea sin permisos. Edítalo después de guardarlo para asignarle una matriz
            de permisos.
          </Typography.Paragraph>
        )}
      </Modal>

      {confirmDeactivate && (
        <ConfirmationModal open title="Desactivar rol"
          description="¿Confirmas la desactivación de este rol? Se bloqueará si tiene usuarios activos asignados."
          onConfirm={() => handleDeactivate(confirmDeactivate)} onCancel={() => setConfirmDeactivate(null)} />
      )}
    </div>
  )
}
