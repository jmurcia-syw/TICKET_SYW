import { useEffect, useState } from 'react'
import { Button, Divider, Form, Input, InputNumber, Modal, Select, Space, Table, Tabs, Tooltip, Upload, message } from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, PlayCircleOutlined, EyeInvisibleOutlined, EyeOutlined, DeleteOutlined, UploadOutlined, DownloadOutlined } from '@ant-design/icons'
import type { ColumnsType, TableProps } from 'antd/es/table'
import PhoneInput, { isValidPhoneNumber } from 'react-phone-number-input'
import 'react-phone-number-input/style.css'
import { clientService } from '../services/clientService'
import { COUNTRIES } from '../data/countries'
import { TIMEZONES } from '../data/timezones'
import apiClient from '../services/apiClient'
import type {
  ClientListItem, ClientDetail, ClientFormData, ClientSystem, ClientSystemFormData,
  ClientAccess, ClientAccessFormData, ClientAccessAttachment, ClientAccessType,
} from '../types/client'

const ACCESS_TYPE_OPTIONS: { value: ClientAccessType; label: string }[] = [
  { value: 'vpn', label: 'VPN' },
  { value: 'system_url', label: 'URL de sistema' },
  { value: 'remote_desktop', label: 'Escritorio remoto' },
]
const ENVIRONMENT_OPTIONS = [
  { value: 'dev', label: 'DEV' }, { value: 'test', label: 'TEST' }, { value: 'prod', label: 'PROD' },
]
import ConfirmationModal from '../components/common/ConfirmationModal'
import { mapApiErrorToFormFields, type FieldErrorRule } from '../services/formErrorMapper'

// OBS-0018: asocia códigos de error de la API a los campos del formulario de Cliente.
const CLIENT_ERROR_RULES: FieldErrorRule[] = [
  { code: 'name_duplicate', field: 'name' },
  { code: 'validation_error', field: 'name', messageIncludes: ["'name'", 'nombre'] },
  { code: 'validation_error', field: 'contact_phone', messageIncludes: ['contact_phone'] },
]
import StatusTag from '../components/common/StatusTag'
import PageToolbar from '../components/common/PageToolbar'
import { textColumnFilter, serverColumnFilter } from '../components/common/columnFilters'
import { palette } from '../theme'
import { useAuthStore } from '../store/authStore'

const ACTIVE_FILTER_OPTIONS = [{ text: 'Activo', value: 'true' }, { text: 'Inactivo', value: 'false' }]

export default function ClientsPage() {
  const { hasPermission, role } = useAuthStore()
  const canManage = hasPermission('clients', 'create') || hasPermission('clients', 'edit') || hasPermission('clients', 'deactivate')
  const canSeeSensitive = role?.name === 'Admin' || role?.name === 'Coordinador'

  const [clients, setClients] = useState<ClientListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>()
  const [loading, setLoading] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [selectedDetail, setSelectedDetail] = useState<ClientDetail | null>(null)
  const [confirmDeactivate, setConfirmDeactivate] = useState<{ id: string; impact: string } | null>(null)
  const [systems, setSystems] = useState<ClientSystem[]>([])
  const [accessList, setAccessList] = useState<ClientAccess[]>([])
  const [accessAttachments, setAccessAttachments] = useState<ClientAccessAttachment[]>([])
  const [revealAccessId, setRevealAccessId] = useState<string | null>(null)
  const [editingAccessId, setEditingAccessId] = useState<string | null>(null)
  const [form] = Form.useForm<ClientFormData>()
  const [systemForm] = Form.useForm<ClientSystemFormData>()
  const [accessForm] = Form.useForm<ClientAccessFormData>()

  const load = async () => {
    setLoading(true)
    try {
      const res = await clientService.list({ page, page_size: 20, search: search || undefined, active: activeFilter })
      setClients(res.items)
      setTotal(res.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [page, search, activeFilter])

  const handleTableChange: TableProps<ClientListItem>['onChange'] = (pagination, filters) => {
    setPage(pagination.current || 1)
    const activeValue = filters.active?.[0] as string | undefined
    setActiveFilter(activeValue === undefined ? undefined : activeValue === 'true')
  }

  const openCreate = () => { form.resetFields(); setEditingId(null); setFormOpen(true) }
  const openEdit = (c: ClientListItem) => {
    form.resetFields()
    form.setFieldsValue(c)
    setEditingId(c.id)
    setFormOpen(true)
  }

  const openDetail = async (id: string) => {
    // Se resetea el estado de inmediato (antes de esperar la respuesta) para no mostrar
    // residualmente los datos del cliente anterior mientras carga (UAT OBS-0008).
    setSelectedDetail(null)
    setSystems([])
    setAccessList([])
    setAccessAttachments([])
    setRevealAccessId(null)
    setEditingAccessId(null)
    accessForm.resetFields()
    const detail = await clientService.get(id)
    setSelectedDetail(detail)
    setSystems(await clientService.listSystems(id))
    setAccessList(await clientService.listAccess(id))
    setAccessAttachments(await clientService.listAccessAttachments(id))
    setDetailOpen(true)
  }

  const handleAccessSubmit = async (values: ClientAccessFormData) => {
    if (!selectedDetail) return
    try {
      if (editingAccessId) {
        await clientService.updateAccess(selectedDetail.id, editingAccessId, values)
        message.success('Acceso actualizado')
      } else {
        await clientService.addAccess(selectedDetail.id, values)
        message.success('Acceso agregado')
      }
      accessForm.resetFields()
      setEditingAccessId(null)
      setAccessList(await clientService.listAccess(selectedDetail.id))
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al guardar el acceso'
      message.error(msg)
    }
  }

  const openEditAccess = (access: ClientAccess) => {
    setEditingAccessId(access.id)
    accessForm.setFieldsValue({
      access_type: access.access_type, environment: access.environment ?? undefined,
      username: access.username ?? undefined, password: access.password ?? undefined,
      host: access.host ?? undefined, notes: access.notes ?? undefined,
    })
  }

  const handleDeleteAccess = async (accessId: string) => {
    if (!selectedDetail) return
    await clientService.deleteAccess(selectedDetail.id, accessId)
    setAccessList(await clientService.listAccess(selectedDetail.id))
    message.success('Acceso eliminado')
  }

  const handleUploadAccessAttachment = async (file: File) => {
    if (!selectedDetail) return false
    try {
      await clientService.uploadAccessAttachment(selectedDetail.id, file)
      setAccessAttachments(await clientService.listAccessAttachments(selectedDetail.id))
      message.success('Adjunto subido')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al subir el adjunto'
      message.error(msg)
    }
    return false
  }

  const handleDeleteAccessAttachment = async (attachmentId: string) => {
    if (!selectedDetail) return
    await clientService.deleteAccessAttachment(selectedDetail.id, attachmentId)
    setAccessAttachments(await clientService.listAccessAttachments(selectedDetail.id))
    message.success('Adjunto eliminado')
  }

  const handleDownloadAccessAttachment = async (attachment: ClientAccessAttachment) => {
    if (!selectedDetail) return
    const url = clientService.downloadAccessAttachmentUrl(selectedDetail.id, attachment.id)
    const res = await apiClient.get(url, { responseType: 'blob' })
    const blobUrl = URL.createObjectURL(res.data as Blob)
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = attachment.filename
    link.click()
    URL.revokeObjectURL(blobUrl)
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
      if (mapApiErrorToFormFields(err, form, CLIENT_ERROR_RULES)) return
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
    {
      title: 'Nombre', dataIndex: 'name', sorter: true, key: 'name',
      ...textColumnFilter('Buscar cliente...', search, setSearch),
    },
    { title: 'Contacto', dataIndex: 'contact_name' },
    { title: 'Email', dataIndex: 'contact_email' },
    {
      title: 'Estado', dataIndex: 'active', key: 'active',
      render: (v: boolean) => <StatusTag active={v} />,
      ...serverColumnFilter(ACTIVE_FILTER_OPTIONS, activeFilter === undefined ? undefined : String(activeFilter)),
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
        pagination={{ current: page, total, pageSize: 20 }}
        onChange={handleTableChange}
      />

      <Modal title={editingId ? 'Editar cliente' : 'Nuevo cliente'} open={formOpen} onCancel={() => setFormOpen(false)} onOk={() => form.submit()} okText="Guardar">
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="Nombre" rules={[
            { required: true, message: 'El nombre es requerido' },
            { max: 120, message: 'Máximo 120 caracteres' },
            {
              validator: (_, value) =>
                !value || /[\p{L}\p{N}]/u.test(value)
                  ? Promise.resolve()
                  : Promise.reject(new Error('El nombre debe contener al menos una letra o número')),
            },
          ]}>
            <Input maxLength={120} />
          </Form.Item>
          <Form.Item name="contact_name" label="Nombre de contacto"><Input /></Form.Item>
          <Form.Item
            name="contact_email" label="Email de contacto" rules={[{ type: 'email', message: 'Email inválido' }]}
            extra="No se verifica que el correo exista realmente, solo el formato."
          >
            <Input />
          </Form.Item>
          <Form.Item name="contact_phone" label="Teléfono" rules={[
            {
              validator: (_, value) =>
                !value || isValidPhoneNumber(value)
                  ? Promise.resolve()
                  : Promise.reject(new Error('Teléfono inválido')),
            },
          ]}>
            <PhoneInput
              defaultCountry="CO" international countryCallingCodeEditable={false} className="sw-phone-input"
              onChange={() => {}}
            />
          </Form.Item>
          <Form.Item name="annual_billing_usd" label="Facturación anual (USD)">
            <InputNumber min={0} style={{ width: '100%' }} formatter={v => `$ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} />
          </Form.Item>
          <Form.Item name="country" label="País" extra="Determina qué festivos se muestran en el Calendario del cliente.">
            <Select allowClear showSearch optionFilterProp="label" style={{ width: '100%' }}
              options={COUNTRIES.map(c => ({ value: c.code, label: c.name }))} />
          </Form.Item>
          <Form.Item name="timezone" label="Huso horario">
            <Select allowClear showSearch style={{ width: '100%' }}
              options={TIMEZONES.map(tz => ({ value: tz, label: tz }))} />
          </Form.Item>
          <Form.Item name="notes" label="Notas"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>

      <Modal title="Detalle del cliente" open={detailOpen} onCancel={() => setDetailOpen(false)} footer={null} width={selectedDetail ? 820 : 520}>
        {selectedDetail && (
          <Tabs
            items={[
              {
                key: 'general', label: 'Datos generales',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div><strong>Nombre:</strong> {selectedDetail.name}</div>
                    <div><strong>Contacto:</strong> {selectedDetail.contact_name}</div>
                    <div><strong>Email:</strong> {selectedDetail.contact_email}</div>
                    <div><strong>Facturación anual (USD):</strong>{' '}
                      {selectedDetail.annual_billing_usd != null
                        ? `$ ${selectedDetail.annual_billing_usd.toLocaleString('en-US')}`
                        : '—'}
                    </div>
                    <div><strong>Notas:</strong> {selectedDetail.notes}</div>
                  </Space>
                ),
              },
              {
                key: 'access', label: 'Accesos y conexiones',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Table
                      rowKey="id"
                      size="small"
                      dataSource={accessList}
                      pagination={false}
                      locale={{ emptyText: 'Sin accesos registrados' }}
                      columns={[
                        { title: 'Tipo', dataIndex: 'access_type', render: (v: string) => ACCESS_TYPE_OPTIONS.find(o => o.value === v)?.label ?? v },
                        { title: 'Ambiente', dataIndex: 'environment', render: (v: string | null) => v ? v.toUpperCase() : '—' },
                        { title: 'Usuario', dataIndex: 'username', render: (v: string | null) => canSeeSensitive ? (v ?? '—') : '—' },
                        {
                          title: 'Contraseña', dataIndex: 'password',
                          render: (v: string | null, row: ClientAccess) => canSeeSensitive ? (
                            <Space>
                              {revealAccessId === row.id ? (v ?? '—') : '••••••••'}
                              <Button size="small" type="link" icon={revealAccessId === row.id ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                                onClick={() => setRevealAccessId(id => id === row.id ? null : row.id)} />
                            </Space>
                          ) : '—',
                        },
                        { title: 'Host/IP/URL', dataIndex: 'host' },
                        { title: 'Notas', dataIndex: 'notes' },
                        ...(canManage ? [{
                          title: '', key: 'actions',
                          render: (_: unknown, row: ClientAccess) => (
                            <Space>
                              <Button size="small" type="text" icon={<EditOutlined />} onClick={() => openEditAccess(row)} />
                              <Button size="small" danger type="text" icon={<DeleteOutlined />} onClick={() => handleDeleteAccess(row.id)} />
                            </Space>
                          ),
                        }] : []),
                      ]}
                    />
                    {canManage && (
                      <Form form={accessForm} layout="inline" onFinish={handleAccessSubmit} style={{ marginTop: 8, rowGap: 8 }}>
                        <Form.Item name="access_type" rules={[{ required: true, message: 'Tipo requerido' }]}>
                          <Select placeholder="Tipo" style={{ width: 150 }} options={ACCESS_TYPE_OPTIONS} />
                        </Form.Item>
                        <Form.Item name="environment">
                          <Select placeholder="Ambiente" allowClear style={{ width: 100 }} options={ENVIRONMENT_OPTIONS} />
                        </Form.Item>
                        <Form.Item name="username"><Input placeholder="Usuario" style={{ width: 120 }} /></Form.Item>
                        <Form.Item name="password"><Input.Password placeholder="Contraseña" style={{ width: 140 }} /></Form.Item>
                        <Form.Item name="host"><Input placeholder="Host/IP/URL" style={{ width: 160 }} /></Form.Item>
                        <Form.Item name="notes"><Input placeholder="Notas" style={{ width: 140 }} /></Form.Item>
                        <Form.Item>
                          <Space>
                            <Button htmlType="submit" icon={<PlusOutlined />}>{editingAccessId ? 'Guardar' : 'Agregar'}</Button>
                            {editingAccessId && (
                              <Button onClick={() => { setEditingAccessId(null); accessForm.resetFields() }}>Cancelar</Button>
                            )}
                          </Space>
                        </Form.Item>
                      </Form>
                    )}

                    <Divider style={{ margin: '12px 0' }}>Adjuntos (instructivos de instalación/configuración)</Divider>
                    <Table
                      rowKey="id"
                      size="small"
                      dataSource={accessAttachments}
                      pagination={false}
                      locale={{ emptyText: 'Sin adjuntos' }}
                      columns={[
                        { title: 'Archivo', dataIndex: 'filename' },
                        {
                          title: '', key: 'actions',
                          render: (_: unknown, a: ClientAccessAttachment) => (
                            <Space>
                              <Button size="small" type="text" icon={<DownloadOutlined />} onClick={() => handleDownloadAccessAttachment(a)} />
                              {canManage && (
                                <Button size="small" danger type="text" icon={<DeleteOutlined />} onClick={() => handleDeleteAccessAttachment(a.id)} />
                              )}
                            </Space>
                          ),
                        },
                      ]}
                    />
                    {canManage && (
                      <Upload beforeUpload={handleUploadAccessAttachment} showUploadList={false}>
                        <Button icon={<UploadOutlined />}>Adjuntar archivo</Button>
                      </Upload>
                    )}
                  </Space>
                ),
              },
              {
                key: 'systems', label: 'Portafolio de software',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
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
                ),
              },
            ]}
          />
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
