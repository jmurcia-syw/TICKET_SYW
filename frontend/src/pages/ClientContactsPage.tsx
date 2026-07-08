import { useEffect, useState } from 'react'
import { Alert, Button, Form, Input, Modal, Select, Space, Table, Typography, message } from 'antd'
import { PlusOutlined, CopyOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { clientContactService } from '../services/clientContactService'
import { clientService } from '../services/clientService'
import type { ClientContact, ClientContactCreateRequest } from '../types/clientContact'
import type { ClientListItem } from '../types/client'
import PageToolbar from '../components/common/PageToolbar'

/** Alta de Encargados (Fase 2.1, US3): usuarios externos de rol Encargado, vinculados a un
 * Cliente fijo, que solo pueden crear/ver sus propios tickets. Gestionado por Admin/Coordinador
 * (permiso `client_contacts:manage`) — mismo patrón simplificado que `TeamPage` para altas. */
export default function ClientContactsPage() {
  const [contacts, setContacts] = useState<ClientContact[]>([])
  const [clients, setClients] = useState<ClientListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [form] = Form.useForm<ClientContactCreateRequest>()
  const [provisionalPassword, setProvisionalPassword] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const res = await clientContactService.list({ page_size: 200 })
      setContacts(res.items)
    } catch {
      message.error('No se pudo cargar la lista de Encargados')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])
  useEffect(() => {
    clientService.list({ active: true, page_size: 200 }).then(r => setClients(r.items))
      .catch(() => message.error('No se pudo cargar la lista de clientes'))
  }, [])

  const handleCreate = async (values: ClientContactCreateRequest) => {
    try {
      const { provisional_password } = await clientContactService.create(values)
      setCreateOpen(false)
      setProvisionalPassword(provisional_password)
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al crear el Encargado'
      message.error(msg)
    }
  }

  const handleCopyPassword = () => {
    if (provisionalPassword) navigator.clipboard.writeText(provisionalPassword)
    message.success('Contraseña copiada')
  }

  const columns: ColumnsType<ClientContact> = [
    { title: 'Email', dataIndex: 'email' },
    { title: 'Usuario', dataIndex: 'username' },
    { title: 'Cliente', dataIndex: 'client_name' },
    { title: 'Alta', dataIndex: 'created_at', render: (v: string) => new Date(v).toLocaleDateString('es-CO') },
  ]

  return (
    <div>
      <PageToolbar
        filters={null}
        action={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { form.resetFields(); setCreateOpen(true) }}>
            Nuevo Encargado
          </Button>
        }
      />

      <Table
        rowKey="id"
        columns={columns}
        dataSource={contacts}
        loading={loading}
        locale={{ emptyText: 'Todavía no hay Encargados dados de alta.' }}
      />

      <Modal title="Nuevo Encargado" open={createOpen} onCancel={() => setCreateOpen(false)}
        onOk={() => form.submit()} okText="Crear">
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="email" label="Email (su correo real, no @sywork.net)"
            rules={[{ required: true, message: 'El email es requerido' }, { type: 'email', message: 'Email inválido' }]}>
            <Input placeholder="contacto@clienteexterno.com" />
          </Form.Item>
          <Form.Item name="username" label="Nombre de usuario" rules={[{ required: true, message: 'El username es requerido' }]}>
            <Input placeholder="nombre.apellido" />
          </Form.Item>
          <Form.Item name="client_id" label="Cliente" rules={[{ required: true, message: 'Selecciona un cliente' }]}>
            <Select showSearch optionFilterProp="label" placeholder="Cliente"
              options={clients.map(c => ({ value: c.id, label: c.name }))} />
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
        <Alert type="warning" showIcon style={{ marginBottom: 16 }}
          message="Esta contraseña no se volverá a mostrar. Compártela ahora con el Encargado por un canal seguro." />
        <Space>
          <Typography.Text code style={{ fontSize: 16 }}>{provisionalPassword}</Typography.Text>
          <Button size="small" icon={<CopyOutlined />} onClick={handleCopyPassword}>Copiar</Button>
        </Space>
      </Modal>
    </div>
  )
}
