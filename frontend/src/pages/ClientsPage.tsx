import { useEffect, useState } from 'react'
import { Button, Divider, Form, Input, InputNumber, Modal, Select, Space, Table, Tooltip, message } from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, PlayCircleOutlined, EyeInvisibleOutlined, EyeOutlined, DeleteOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { clientService } from '../services/clientService'
import type { ClientListItem, ClientDetail, ClientFormData, ClientSystem, ClientSystemFormData } from '../types/client'
import ConfirmationModal from '../components/common/ConfirmationModal'
import StatusTag from '../components/common/StatusTag'
import PageToolbar from '../components/common/PageToolbar'
import { palette } from '../theme'
import { useAuthStore } from '../store/authStore'

export default function ClientsPage() {
  const { hasPermission, role } = useAuthStore()
  const canManage = hasPermission('clients', 'create') || hasPermission('clients', 'edit') || hasPermission('clients', 'deactivate')
  const canSeeSensitive = role?.name === 'Admin' || role?.name === 'Coordinador'

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
  const [systems, setSystems] = useState<ClientSystem[]>([])
  const [form] = Form.useForm<ClientFormData>()
  const [systemForm] = Form.useForm<ClientSystemFormData>()

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
    setSystems(await clientService.listSystems(id))
    setDetailOpen(true)
  }

  const handleAddSystem = async (values: ClientSystemFormData) => {
    if (!selectedDetail) return
    try {
      await clientService.addSystem(selectedDetail.id, values)
      systemForm.resetFields()
      setSystems(await clientService.listSystems(selectedDetail.id))
      message.success('Sistema agregado')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al agregar el sistema'
      message.error(msg)
    }
  }

  const handleDeleteSystem = async (systemId: string) => {
    if (!selectedDetail) return
    await clientService.deleteSystem(selectedDetail.id, systemId)
    setSystems(await clientService.listSystems(selectedDetail.id))
    message.success('Sistema eliminado')
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

  const handleActivate = async (id: string) => {
    await clientService.activate(id)
    message.success('Cliente activado')
    load()
  }

  const columns: ColumnsType<ClientListItem> = [
    { title: 'Nombre', dataIndex: 'name', sorter: true },
    { title: 'Contacto', dataIndex: 'contact_name' },
    { title: 'Email', dataIndex: 'contact_email' },
    {
      title: 'Estado', dataIndex: 'active',
      render: (v: boolean) => <StatusTag active={v} />,
    },
    {
      title: 'Acciones', key: 'actions',
      render: (_: unknown, record: ClientListItem) => (
        <Space>
          <Tooltip title="Ver detalle"><Button size="small" icon={<EyeOutlined />} onClick={() => openDetail(record.id)} /></Tooltip>
          {canManage && <Tooltip title="Editar"><Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)} /></Tooltip>}
          {canManage && (record.active
            ? <Tooltip title="Desactivar"><Button size="small" danger icon={<StopOutlined />} onClick={() => handleDeactivate(record.id)} /></Tooltip>
            : <Tooltip title="Activar"><Button size="small" icon={<PlayCircleOutlined style={{ color: palette.green600 }} />} onClick={() => handleActivate(record.id)} /></Tooltip>)}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <PageToolbar
        filters={<Input.Search placeholder="Buscar cliente..." onSearch={setSearch} allowClear style={{ width: 300 }} />}
        action={canManage && <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>Nuevo cliente</Button>}
      />

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
          <Form.Item name="annual_billing_usd" label="Facturación anual (USD)">
            <InputNumber min={0} style={{ width: '100%' }} formatter={v => `$ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} />
          </Form.Item>
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
            {canSeeSensitive && (
              <>
                <div>
                  <strong>IPs VPN:</strong>{' '}
                  {revealVpn ? selectedDetail.vpn_ips : '••••••••'}{' '}
                  <Button size="small" type="link" icon={revealVpn ? <EyeInvisibleOutlined /> : <EyeOutlined />} onClick={() => setRevealVpn(v => !v)} />
                </div>
                <div>
                  <strong>Credenciales VPN:</strong>{' '}
                  {revealVpn ? selectedDetail.vpn_credentials : '••••••••'}
                </div>
              </>
            )}
            <div><strong>Facturación anual (USD):</strong>{' '}
              {selectedDetail.annual_billing_usd != null
                ? `$ ${selectedDetail.annual_billing_usd.toLocaleString('en-US')}`
                : '—'}
            </div>
            <div><strong>Notas:</strong> {selectedDetail.notes}</div>

            <Divider style={{ margin: '12px 0' }}>Portafolio de software</Divider>
            <Table
              rowKey="id"
              size="small"
              dataSource={systems}
              pagination={false}
              locale={{ emptyText: 'Sin sistemas registrados' }}
              columns={[
                { title: 'Tipo', dataIndex: 'system_type' },
                { title: 'Marca', dataIndex: 'brand' },
                { title: 'Versión', dataIndex: 'version' },
                ...(canManage ? [{
                  title: '', key: 'del',
                  render: (_: unknown, s: ClientSystem) => (
                    <Button size="small" danger type="text" icon={<DeleteOutlined />} onClick={() => handleDeleteSystem(s.id)} />
                  ),
                }] : []),
              ]}
            />
            {canManage && (
              <Form form={systemForm} layout="inline" onFinish={handleAddSystem} style={{ marginTop: 8 }}>
                <Form.Item name="system_type" rules={[{ required: true, message: 'Tipo requerido' }]}>
                  <Select placeholder="Tipo" style={{ width: 110 }} options={['ERP', 'WMS', 'CRM', 'OTM', 'Otro'].map(v => ({ value: v, label: v }))} />
                </Form.Item>
                <Form.Item name="brand" rules={[{ required: true, message: 'Marca requerida' }]}>
                  <Input placeholder="Marca (ej. JD Edwards)" style={{ width: 170 }} />
                </Form.Item>
                <Form.Item name="version"><Input placeholder="Versión" style={{ width: 90 }} /></Form.Item>
                <Form.Item><Button htmlType="submit" icon={<PlusOutlined />}>Agregar</Button></Form.Item>
              </Form>
            )}
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
