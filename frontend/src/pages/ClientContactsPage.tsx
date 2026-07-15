import { useCallback, useEffect, useState } from 'react'
import { Alert, Button, Form, Input, Modal, Select, Space, Table, Tag, Typography, message } from 'antd'
import { PlusOutlined, CopyOutlined, ProjectOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { clientContactService } from '../services/clientContactService'
import { clientService } from '../services/clientService'
import { projectService } from '../services/projectService'
import type { ClientContact, ClientContactCreateRequest } from '../types/clientContact'
import type { ClientListItem } from '../types/client'
import type { ProjectListItem } from '../types/project'
import PageToolbar from '../components/common/PageToolbar'

/** Alta y consulta de Usuarios/cliente (spec 010): usuarios externos de rol Usuario/cliente.
 * La relación operativa es con el **Proyecto** — el alta elige Proyecto, el Cliente se deriva
 * de él y la membresía en el personal del proyecto se crea automáticamente. Gestionado por
 * Admin/Coordinador (permiso `client_contacts:manage`). */
export default function ClientContactsPage() {
  const [contacts, setContacts] = useState<ClientContact[]>([])
  const [clients, setClients] = useState<ClientListItem[]>([])
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [form] = Form.useForm<ClientContactCreateRequest>()
  const [provisionalPassword, setProvisionalPassword] = useState<string | null>(null)

  const [managingContact, setManagingContact] = useState<ClientContact | null>(null)
  const [projectToAdd, setProjectToAdd] = useState<string | undefined>()
  const [managingBusy, setManagingBusy] = useState(false)

  const [emailFilter, setEmailFilter] = useState('')
  const [usernameFilter, setUsernameFilter] = useState('')
  const [clientFilter, setClientFilter] = useState<string | undefined>()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await clientContactService.list({
        page_size: 200,
        email: emailFilter.trim() || undefined,
        username: usernameFilter.trim() || undefined,
        client_id: clientFilter,
      })
      setContacts(res.items)
    } catch {
      message.error('No se pudo cargar la lista de Usuarios/cliente')
    } finally {
      setLoading(false)
    }
  }, [emailFilter, usernameFilter, clientFilter])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    clientService.list({ active: true, page_size: 200 }).then(r => setClients(r.items))
      .catch(() => message.error('No se pudo cargar la lista de clientes'))
    projectService.list({ active: true, page_size: 200 }).then(r => setProjects(r.items))
      .catch(() => message.error('No se pudo cargar la lista de proyectos'))
  }, [])

  const handleCreate = async (values: ClientContactCreateRequest) => {
    try {
      const { provisional_password } = await clientContactService.create(values)
      setCreateOpen(false)
      setProvisionalPassword(provisional_password)
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al crear el Usuario/cliente'
      message.error(msg)
    }
  }

  const handleCopyPassword = () => {
    if (provisionalPassword) navigator.clipboard.writeText(provisionalPassword)
    message.success('Contraseña copiada')
  }

  const handleAddProject = async () => {
    if (!managingContact || !projectToAdd) return
    setManagingBusy(true)
    try {
      await clientContactService.addProject(managingContact.id, projectToAdd)
      setProjectToAdd(undefined)
      const res = await clientContactService.list({ page_size: 200, email: managingContact.email })
      const updated = res.items.find(c => c.id === managingContact.id)
      if (updated) setManagingContact(updated)
      load()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'No se pudo agregar el proyecto'
      message.error(msg)
    } finally {
      setManagingBusy(false)
    }
  }

  const handleRemoveProject = async (projectId: string) => {
    if (!managingContact) return
    setManagingBusy(true)
    try {
      await clientContactService.removeProject(managingContact.id, projectId)
      setManagingContact({ ...managingContact, projects: managingContact.projects.filter(p => p.id !== projectId) })
      load()
    } catch {
      message.error('No se pudo quitar el proyecto')
    } finally {
      setManagingBusy(false)
    }
  }

  const columns: ColumnsType<ClientContact> = [
    { title: 'Email', dataIndex: 'email' },
    { title: 'Usuario', dataIndex: 'username' },
    { title: 'Cliente', dataIndex: 'client_name' },
    {
      title: 'Proyectos', dataIndex: 'projects',
      render: (projects: ClientContact['projects']) => projects.length === 0
        ? <Typography.Text type="secondary">Sin proyecto</Typography.Text>
        : <Space size={4} wrap>{projects.map(p => <Tag key={p.id}>{p.name}</Tag>)}</Space>,
    },
    { title: 'Alta', dataIndex: 'created_at', render: (v: string) => new Date(v).toLocaleDateString('es-CO') },
    {
      title: 'Acciones',
      render: (_: unknown, contact: ClientContact) => (
        <Button size="small" icon={<ProjectOutlined />} onClick={() => setManagingContact(contact)}>
          Gestionar proyectos
        </Button>
      ),
    },
  ]

  return (
    <div>
      <PageToolbar
        filters={<>
          <Input.Search placeholder="Buscar por email..." allowClear style={{ width: 220 }}
            onSearch={setEmailFilter} />
          <Input.Search placeholder="Buscar por usuario..." allowClear style={{ width: 200 }}
            onSearch={setUsernameFilter} />
          <Select placeholder="Filtrar por cliente" allowClear showSearch optionFilterProp="label"
            style={{ width: 200 }} onChange={setClientFilter}
            options={clients.map(c => ({ value: c.id, label: c.name }))} />
        </>}
        action={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { form.resetFields(); setCreateOpen(true) }}>
            Nuevo Usuario/cliente
          </Button>
        }
      />

      <Table
        rowKey="id"
        columns={columns}
        dataSource={contacts}
        loading={loading}
        locale={{ emptyText: 'Todavía no hay Usuarios/cliente dados de alta.' }}
      />

      <Modal title="Nuevo Usuario/cliente" open={createOpen} onCancel={() => setCreateOpen(false)}
        onOk={() => form.submit()} okText="Crear">
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="email" label="Email (su correo real, no @sywork.net)"
            rules={[{ required: true, message: 'El email es requerido' }, { type: 'email', message: 'Email inválido' }]}>
            <Input placeholder="contacto@clienteexterno.com" />
          </Form.Item>
          <Form.Item name="username" label="Nombre de usuario" rules={[{ required: true, message: 'El username es requerido' }]}>
            <Input placeholder="nombre.apellido" />
          </Form.Item>
          <Form.Item name="project_ids" label="Proyectos"
            extra="El Cliente se deriva de los proyectos (deben ser todos del mismo Cliente) y la persona queda en su personal automáticamente."
            rules={[{ required: true, type: 'array', min: 1, message: 'Selecciona al menos un proyecto' }]}>
            <Select mode="multiple" showSearch optionFilterProp="label" placeholder="Proyectos"
              options={projects.map(p => ({
                value: p.id,
                label: p.client_name ? `${p.client_name} — ${p.name}` : p.name,
              }))} />
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
          message="Esta contraseña no se volverá a mostrar. Compártela ahora con el Usuario/cliente por un canal seguro." />
        <Space>
          <Typography.Text code style={{ fontSize: 16 }}>{provisionalPassword}</Typography.Text>
          <Button size="small" icon={<CopyOutlined />} onClick={handleCopyPassword}>Copiar</Button>
        </Space>
      </Modal>

      <Modal
        title={managingContact ? `Proyectos de ${managingContact.username}` : 'Proyectos'}
        open={!!managingContact}
        onCancel={() => { setManagingContact(null); setProjectToAdd(undefined) }}
        footer={<Button onClick={() => { setManagingContact(null); setProjectToAdd(undefined) }}>Cerrar</Button>}
      >
        {managingContact && <>
          <div style={{ marginBottom: 16 }}>
            {managingContact.projects.length === 0
              ? <Typography.Text type="secondary">Sin proyectos asignados.</Typography.Text>
              : <Space size={4} wrap>
                  {managingContact.projects.map(p => (
                    <Tag key={p.id} closable onClose={(e) => { e.preventDefault(); handleRemoveProject(p.id) }}>
                      {p.name}
                    </Tag>
                  ))}
                </Space>}
          </div>
          <Space.Compact style={{ width: '100%' }}>
            <Select
              style={{ width: '100%' }}
              showSearch optionFilterProp="label" placeholder="Agregar proyecto"
              value={projectToAdd} onChange={setProjectToAdd}
              options={projects
                .filter(p => (managingContact.projects.length === 0 || p.client_id === managingContact.client_id)
                  && !managingContact.projects.some(mp => mp.id === p.id))
                .map(p => ({
                  value: p.id,
                  label: p.client_name ? `${p.client_name} — ${p.name}` : p.name,
                }))}
            />
            <Button type="primary" disabled={!projectToAdd} loading={managingBusy} onClick={handleAddProject}>
              Agregar
            </Button>
          </Space.Compact>
        </>}
      </Modal>
    </div>
  )
}
