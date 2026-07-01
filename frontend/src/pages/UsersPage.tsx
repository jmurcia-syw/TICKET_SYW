import { useEffect, useState } from 'react'
import { Button, Form, Modal, Select, Space, Table, Tag, Tooltip, message } from 'antd'
import { EditOutlined, StopOutlined, PlayCircleOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { userService } from '../services/userService'
import type { UserAdmin } from '../types/user'
import type { Role } from '../types/api'
import ConfirmationModal from '../components/common/ConfirmationModal'
import StatusTag from '../components/common/StatusTag'
import { ROLE_COLORS, palette } from '../theme'

const ROLES: Role[] = ['admin', 'coordinator', 'qm', 'resolver']
const ROLE_LABELS: Record<Role, string> = { admin: 'Admin', coordinator: 'Coordinador', qm: 'QM', resolver: 'Resolutor' }

export default function UsersPage() {
  const [users, setUsers] = useState<UserAdmin[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [roleFormOpen, setRoleFormOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<UserAdmin | null>(null)
  const [confirmDeactivate, setConfirmDeactivate] = useState<string | null>(null)
  const [form] = Form.useForm<{ role: Role }>()

  const load = async () => {
    setLoading(true)
    try {
      const res = await userService.list({ page, page_size: 20 })
      setUsers(res.items)
      setTotal(res.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [page])

  const openRoleChange = (u: UserAdmin) => {
    form.setFieldsValue({ role: u.role })
    setEditingUser(u)
    setRoleFormOpen(true)
  }

  const handleRoleSubmit = async ({ role }: { role: Role }) => {
    if (!editingUser) return
    try {
      await userService.changeRole(editingUser.id, role)
      message.success('Rol actualizado')
      setRoleFormOpen(false)
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al cambiar el rol'
      message.error(msg)
    }
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
    { title: 'Email', dataIndex: 'email' },
    {
      title: 'Rol', dataIndex: 'role',
      render: (r: Role) => <Tag color={ROLE_COLORS[r]}>{ROLE_LABELS[r]}</Tag>,
    },
    { title: 'Estado', dataIndex: 'active', render: (v: boolean) => <StatusTag active={v} /> },
    { title: 'Último acceso', dataIndex: 'last_login_at', render: (v: string | null) => <span className="tabular-nums">{v ? new Date(v).toLocaleDateString('es-CO') : '—'}</span> },
    {
      title: 'Acciones', key: 'actions',
      render: (_: unknown, u: UserAdmin) => (
        <Space>
          <Tooltip title="Cambiar rol"><Button size="small" icon={<EditOutlined />} onClick={() => openRoleChange(u)} /></Tooltip>
          {u.active
            ? <Tooltip title="Desactivar"><Button size="small" danger icon={<StopOutlined />} onClick={() => setConfirmDeactivate(u.id)} /></Tooltip>
            : <Tooltip title="Activar"><Button size="small" icon={<PlayCircleOutlined style={{ color: palette.green600 }} />} onClick={() => handleActivate(u.id)} /></Tooltip>}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Table rowKey="id" columns={columns} dataSource={users} loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage }} />

      <Modal title="Cambiar rol" open={roleFormOpen} onCancel={() => setRoleFormOpen(false)} onOk={() => form.submit()} okText="Guardar">
        <Form form={form} layout="vertical" onFinish={handleRoleSubmit}>
          <Form.Item name="role" label="Nuevo rol" rules={[{ required: true, message: 'Selecciona un rol' }]}>
            <Select options={ROLES.map(r => ({ value: r, label: ROLE_LABELS[r] }))} />
          </Form.Item>
        </Form>
      </Modal>

      {confirmDeactivate && (
        <ConfirmationModal open title="Desactivar usuario"
          description="¿Confirmas la desactivación de este usuario? Perderá acceso inmediatamente en su próxima llamada a la API."
          onConfirm={() => handleDeactivate(confirmDeactivate)} onCancel={() => setConfirmDeactivate(null)} />
      )}
    </div>
  )
}
