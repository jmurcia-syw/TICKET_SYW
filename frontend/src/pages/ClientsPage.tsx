import { useEffect, useState } from 'react'
import { Button, Form, Input, Modal, Space, Table, Tag, Tooltip, message } from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, EyeInvisibleOutlined, EyeOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { clientService } from '../services/clientService'
import type { ClientListItem, ClientDetail, ClientFormData } from '../types/client'
import ConfirmationModal from '../components/common/ConfirmationModal'

export default function ClientsPage() {
  const [clients, setClients] = useState<ClientListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [selectedDetail, setSelectedDetail] = useState<ClientDetail | null>(null)
  const [revealVpn, setRevealVpn] = useState(false)
  const [confirmDeactivate, setConfirmDeactivate] = useState<{ id: string; impact: string } | null>(null)
  const [form] = Form.useForm<ClientFormData>()

  const load = async () => {
    setLoading(true)
    try {
      const res = await clientService.list({ page, page_size: 20, search: search || undefined })
      setClients(res.items)
      setTotal(res.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [page, search])

  const openCreate = () => { form.resetFields(); setEditingId(null); setFormOpen(true) }
  const openEdit = (c: ClientListItem) => { form.setFieldsValue(c); setEditingId(c.id); setFormOpen(true) }

  const openDetail = async (id: string) => {
    const detail = await clientService.get(id)
    setSelectedDetail(detail)
    setRevealVpn(false)
    setDetailOpen(true)
  }

  const handleSubmit = async (values: ClientFormData) => {
    try {
      if (editingId) {
        await clientService.update(editingId, values)
        message.success('Cliente actualizado')
      } else {
        await clientService.create(values)
        message.success('Cliente creado')
      }
      setFormOpen(false)
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al guardar'
      message.error(msg)
    }
  }

  const handleDeactivate = async (id: string) => {
    const res = await clientService.deactivate(id)
    const impact = res.warning ?? 'Cliente desactivado'
    if (res.active_projects_count && res.active_projects_count > 0) {
      setConfirmDeactivate({ id, impact })
    } else {
      message.success('Cliente desactivado')
      load()
    }
  }

  const columns: ColumnsType<ClientListItem> = [
    { title: 'Nombre', dataIndex: 'name', sorter: true },
    { title: 'Contacto', dataIndex: 'contact_name' },
    { title: 'Email', dataIndex: 'contact_email' },
    {
      title: 'Estado', dataIndex: 'active',
      render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? 'Activo' : 'Inactivo'}</Tag>,
    },
    {
      title: 'Acciones', key: 'actions',
      render: (_: unknown, record: ClientListItem) => (
        <Space>
          <Tooltip title="Ver detalle"><Button size="small" icon={<EyeOutlined />} onClick={() => openDetail(record.id)} /></Tooltip>
          <Tooltip title="Editar"><Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)} /></Tooltip>
          {record.active && <Tooltip title="Desactivar"><Button size="small" danger icon={<StopOutlined />} onClick={() => handleDeactivate(record.id)} /></Tooltip>}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Input.Search placeholder="Buscar cliente..." onSearch={setSearch} allowClear style={{ width: 300 }} />
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Nuevo cliente</Button>
      </div>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={clients}
        loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: setPage }}
      />

      <Modal title={editingId ? 'Editar cliente' : 'Nuevo cliente'} open={formOpen} onCancel={() => setFormOpen(false)} onOk={() => form.submit()} okText="Guardar">
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="Nombre" rules={[{ required: true, message: 'El nombre es requerido' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="contact_name" label="Nombre de contacto"><Input /></Form.Item>
          <Form.Item name="contact_email" label="Email de contacto" rules={[{ type: 'email', message: 'Email inválido' }]}><Input /></Form.Item>
          <Form.Item name="contact_phone" label="Teléfono"><Input /></Form.Item>
          <Form.Item name="vpn_ips" label="IPs VPN"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="vpn_credentials" label="Credenciales VPN"><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="notes" label="Notas"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>

      <Modal title="Detalle del cliente" open={detailOpen} onCancel={() => setDetailOpen(false)} footer={null}>
        {selectedDetail && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <div><strong>Nombre:</strong> {selectedDetail.name}</div>
            <div><strong>Contacto:</strong> {selectedDetail.contact_name}</div>
            <div><strong>Email:</strong> {selectedDetail.contact_email}</div>
            <div>
              <strong>IPs VPN:</strong>{' '}
              {revealVpn ? selectedDetail.vpn_ips : '••••••••'}{' '}
              <Button size="small" type="link" icon={revealVpn ? <EyeInvisibleOutlined /> : <EyeOutlined />} onClick={() => setRevealVpn(v => !v)} />
            </div>
            <div>
              <strong>Credenciales VPN:</strong>{' '}
              {revealVpn ? selectedDetail.vpn_credentials : '••••••••'}
            </div>
            <div><strong>Notas:</strong> {selectedDetail.notes}</div>
          </Space>
        )}
      </Modal>

      {confirmDeactivate && (
        <ConfirmationModal
          open
          title="Confirmar desactivación"
          description={confirmDeactivate.impact}
          onConfirm={() => { setConfirmDeactivate(null); load() }}
          onCancel={() => setConfirmDeactivate(null)}
        />
      )}
    </div>
  )
}
