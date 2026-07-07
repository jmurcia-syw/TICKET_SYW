import { useEffect, useState } from 'react'
import { Alert, Button, Form, Input, Modal, Select, Space, Table, Tag, Tooltip, Typography, message } from 'antd'
import { CopyOutlined, EditOutlined, PlusOutlined, PlayCircleOutlined, StopOutlined, KeyOutlined } from '@ant-design/icons'
import type { ColumnsType, TableProps } from 'antd/es/table'
import { userService } from '../services/userService'
import { roleService } from '../services/roleService'
import type { UserAdmin, UserCreateRequest } from '../types/user'
import type { RoleDetail } from '../types/role'
import ConfirmationModal from '../components/common/ConfirmationModal'
import StatusTag from '../components/common/StatusTag'
import PageToolbar from '../components/common/PageToolbar'
import { serverColumnFilter } from '../components/common/columnFilters'
import { useAuthStore } from '../store/authStore'
import { roleColor, palette } from '../theme'

const ACTIVE_FILTER_OPTIONS = [{ text: 'Activo', value: 'true' }, { text: 'Inactivo', value: 'false' }]

export default function UsersPage() {
  const { hasPermission } = useAuthStore()
  const canCreate = hasPermission('users', 'create')
  const canChangeRole = hasPermission('users', 'edit')
  const canDeactivate = hasPermission('users', 'deactivate')

  const [users, setUsers] = useState<UserAdmin[]>([])
  const [roles, setRoles] = useState<RoleDetail[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [roleFilter, setRoleFilter] = useState<string | undefined>()
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>()
  const [loading, setLoading] = useState(false)

  const [roleFormOpen, setRoleFormOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<UserAdmin | null>(null)
  const [roleForm] = Form.useForm<{ role_id: string }>()

  const [createFormOpen, setCreateFormOpen] = useState(false)
  const [createForm] = Form.useForm<UserCreateRequest>()
  const [provisionalPassword, setProvisionalPassword] = useState<string | null>(null)

  const [confirmDeactivate, setConfirmDeactivate] = useState<string | null>(null)
  const [confirmResetPassword, setConfirmResetPassword] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const res = await userService.list({ page, page_size: 20, role: roleFilter, active: activeFilter })
      setUsers(res.items)
      setTotal(res.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [page, roleFilter, activeFilter])
  useEffect(() => { roleService.list({ page_size: 100, active: true }).then(r => setRoles(r.items)) }, [])

  const handleTableChange: TableProps<UserAdmin>['onChange'] = (pagination, filters) => {
    setPage(pagination.current || 1)
    setRoleFilter((filters.role?.[0] as string) || undefined)
    const activeValue = filters.active?.[0] as string | undefined
    setActiveFilter(activeValue === undefined ? undefined : activeValue === 'true')
  }

  const openRoleChange = (u: UserAdmin) => {
    roleForm.setFieldsValue({ role_id: u.role.id })
    setEditingUser(u)
    setRoleFormOpen(true)
  }

  const handleRoleSubmit = async ({ role_id }: { role_id: string }) => {
    if (!editingUser) return
    try {
      await userService.changeRole(editingUser.id, role_id)
      message.success('Rol actualizado')
      setRoleFormOpen(false)
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al cambiar el rol'
      message.error(msg)
    }
  }

  const openCreate = () => { createForm.resetFields(); setCreateFormOpen(true) }

  const handleCreateSubmit = async (values: UserCreateRequest) => {
    try {
      const { provisional_password } = await userService.create(values)
      setCreateFormOpen(false)
      setProvisionalPassword(provisional_password)
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al crear el usuario'
      message.error(msg)
    }
  }

  const handleCopyPassword = () => {
    if (provisionalPassword) navigator.clipboard.writeText(provisionalPassword)
    message.success('Contraseña copiada')
  }

  const handleDeactivate = async (id: string) => {
    try {
      await userService.deactivate(id)
      message.success('Usuario desactivado')
      setConfirmDeactivate(null)
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al desactivar'
      message.error(msg)
    }
  }

  const handleResetPassword = async (id: string) => {
    try {
      const { provisional_password } = await userService.resetPassword(id)
      setConfirmResetPassword(null)
      setProvisionalPassword(provisional_password)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al resetear la contraseña'
      message.error(msg)
    }
  }

  const handleActivate = async (id: string) => {
    try {
      await userService.activate(id)
      message.success('Usuario activado')
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al activar'
      message.error(msg)
    }
  }

  const columns: ColumnsType<UserAdmin> = [
    { title: 'Usuario', dataIndex: 'username' },
    { title: 'Email', dataIndex: 'email' },
    {
      title: 'Rol', dataIndex: 'role', key: 'role',
      render: (r: UserAdmin['role']) => <Tag color={roleColor(r.name)}>{r.name}</Tag>,
      ...serverColumnFilter(roles.map(r => ({ text: r.name, value: r.name })), roleFilter),
    },
    {
      title: 'Estado', dataIndex: 'active', key: 'active',
      render: (v: boolean) => <StatusTag active={v} />,
      ...serverColumnFilter(ACTIVE_FILTER_OPTIONS, activeFilter === undefined ? undefined : String(activeFilter)),
    },
    { title: 'Último acceso', dataIndex: 'last_login_at', render: (v: string | null) => <span className="tabular-nums">{v ? new Date(v).toLocaleDateString('es-CO') : '—'}</span> },
    {
      title: 'Acciones', key: 'actions',
      render: (_: unknown, u: UserAdmin) => (
        <Space>
          {canChangeRole && <Tooltip title="Cambiar rol"><Button size="small" icon={<EditOutlined />} onClick={() => openRoleChange(u)} /></Tooltip>}
          {canChangeRole && <Tooltip title="Resetear contraseña"><Button size="small" icon={<KeyOutlined />} onClick={() => setConfirmResetPassword(u.id)} /></Tooltip>}
          {canDeactivate && (u.active
            ? <Tooltip title="Desactivar"><Button size="small" danger icon={<StopOutlined />} onClick={() => setConfirmDeactivate(u.id)} /></Tooltip>
            : <Tooltip title="Activar"><Button size="small" icon={<PlayCircleOutlined style={{ color: palette.green600 }} />} onClick={() => handleActivate(u.id)} /></Tooltip>)}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageToolbar
        filters={null}
        action={canCreate && <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Nuevo usuario</Button>}
      />

      <Table rowKey="id" columns={columns} dataSource={users} loading={loading}
        pagination={{ current: page, total, pageSize: 20 }} onChange={handleTableChange} />

      <Modal title="Cambiar rol" open={roleFormOpen} onCancel={() => setRoleFormOpen(false)} onOk={() => roleForm.submit()} okText="Guardar">
        <Form form={roleForm} layout="vertical" onFinish={handleRoleSubmit}>
          <Form.Item name="role_id" label="Nuevo rol" rules={[{ required: true, message: 'Selecciona un rol' }]}>
            <Select options={roles.map(r => ({ value: r.id, label: r.name }))} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="Nuevo usuario" open={createFormOpen} onCancel={() => setCreateFormOpen(false)} onOk={() => createForm.submit()} okText="Crear">
        <Form form={createForm} layout="vertical" onFinish={handleCreateSubmit}>
          <Form.Item name="email" label="Email (@sywork.net)" rules={[
            { required: true, message: 'El email es requerido' },
            { pattern: /^[^@]+@sywork\.net$/, message: 'Debe ser @sywork.net' },
          ]}>
            <Input placeholder="nombre.apellido@sywork.net" />
          </Form.Item>
          <Form.Item name="username" label="Nombre de usuario" rules={[{ required: true, message: 'El username es requerido' }]}>
            <Input placeholder="nombre.apellido" />
          </Form.Item>
          <Form.Item name="role_id" label="Rol" rules={[{ required: true, message: 'Selecciona un rol' }]}>
            <Select options={roles.map(r => ({ value: r.id, label: r.name }))} placeholder="Seleccionar rol" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Contraseña provisional generada"
        open={!!provisionalPassword}
        closable={false}
        maskClosable={false}
        footer={<Button type="primary" onClick={() => setProvisionalPassword(null)}>Ya la copié, cerrar</Button>}
      >
        <Alert
          type="warning"
          showIcon
          message="Esta contraseña no se volverá a mostrar. Compártela ahora con el usuario por un canal seguro."
          style={{ marginBottom: 16 }}
        />
        <Space>
          <Typography.Text code style={{ fontSize: 16 }}>{provisionalPassword}</Typography.Text>
          <Button size="small" icon={<CopyOutlined />} onClick={handleCopyPassword}>Copiar</Button>
        </Space>
      </Modal>

      {confirmDeactivate && (
        <ConfirmationModal open title="Desactivar usuario"
          description="¿Confirmas la desactivación de este usuario? Perderá acceso inmediatamente en su próxima llamada a la API."
          onConfirm={() => handleDeactivate(confirmDeactivate)} onCancel={() => setConfirmDeactivate(null)} />
      )}

      {confirmResetPassword && (
        <ConfirmationModal open title="Resetear contraseña"
          description="¿Confirmas resetear la contraseña de este usuario? Se generará una nueva contraseña temporal y la actual dejará de funcionar."
          onConfirm={() => handleResetPassword(confirmResetPassword)} onCancel={() => setConfirmResetPassword(null)} />
      )}
    </div>
  )
}
