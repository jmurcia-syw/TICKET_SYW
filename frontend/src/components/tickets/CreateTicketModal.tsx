import { useEffect, useState } from 'react'
import { Alert, App, Button, Descriptions, Form, Input, Modal, Segmented, Select, Space, Upload } from 'antd'
import { PlusOutlined, UploadOutlined } from '@ant-design/icons'
import type { DefaultOptionType } from 'antd/es/select'
import type { UploadFile } from 'antd'
import { ticketService } from '../../services/ticketService'
import { clientService } from '../../services/clientService'
import { projectService } from '../../services/projectService'
import { clientContactService } from '../../services/clientContactService'
import { catalogService } from '../../services/catalogService'
import { skillService } from '../../services/resourceService'
import { taskListService } from '../../services/taskListService'
import { slaService } from '../../services/slaService'
import type { SlaRule } from '../../types/sla'
import type { TicketFormData, Priority } from '../../types/ticket'
import { TICKET_TYPE_LABELS, PRIORITY_LABELS, SEVERITY_LABELS } from '../../types/ticket'
import type { CatalogItem, ToolProcessLink } from '../../types/catalog'
import type { ClientListItem } from '../../types/client'
import type { ProjectListItem } from '../../types/project'
import type { Skill } from '../../types/resource'
import type { ClientContact } from '../../types/clientContact'
import type { TaskList } from '../../types/taskList'
import { useAuthStore } from '../../store/authStore'
import RichTextEditor, { isRichTextEmpty } from './RichTextEditor'
import { mapApiErrorToFormFields, type FieldErrorRule } from '../../services/formErrorMapper'

// OBS-0034 (spec 028): mismos rangos Unicode que `backend/domain/services/ticket_service.py`
// (`_EMOJI_RANGES`) — letras (incl. acentos/ñ), números y puntuación común quedan permitidos.
const EMOJI_PATTERN = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{1F1E6}-\u{1F1FF}\u{FE0F}\u{200D}]/u

const TITLE_RULES = [
  { required: true, whitespace: true, message: 'El título es requerido' },
  {
    validator: (_: unknown, value: string) =>
      value && EMOJI_PATTERN.test(value)
        ? Promise.reject(new Error('El título no admite emojis'))
        : Promise.resolve(),
  },
]

// OBS-0018: asocia códigos de error de la API a los campos del formulario de creación de Ticket/Tarea.
const TICKET_ERROR_RULES: FieldErrorRule[] = [
  { code: 'title_blank', field: 'title' },
  { code: 'title_invalid_chars', field: 'title' },
  { code: 'validation_error', field: 'client_id', messageIncludes: ['client_id'] },
  { code: 'validation_error', field: 'project_id', messageIncludes: ["'project_id'", 'proyecto no pertenece'] },
  { code: 'validation_error', field: 'client_contact_id', messageIncludes: ["'client_contact_id'"] },
  { code: 'client_inactive', field: 'client_id' },
  { code: 'project_inactive', field: 'project_id' },
  { code: 'project_not_assigned', field: 'project_id' },
  { code: 'catalog_inactive', field: 'tool_id', messageIncludes: ['herramienta'] },
  { code: 'catalog_inactive', field: 'process_id', messageIncludes: ['proceso'] },
  { code: 'catalog_inactive', field: 'record_type_id', messageIncludes: ['tipo de registro'] },
  { code: 'client_contact_mismatch', field: 'client_contact_id' },
  { code: 'contact_not_in_project', field: 'client_contact_id' },
  { code: 'list_mismatch', field: 'list_id' },
]

const priorityOptions = Object.entries(PRIORITY_LABELS).map(([value, label]) => ({ value, label }))
const severityOptions = Object.entries(SEVERITY_LABELS).map(([value, label]) => ({ value, label }))
const typeOptions = Object.entries(TICKET_TYPE_LABELS).map(([value, label]) => ({ value, label }))

/** Botón "Nuevo ticket" + modal de creación de Ticket/Tarea, extraído de `TicketsPage.tsx`
 * (spec 038, US1) para que también esté disponible desde `KanbanPage.tsx`: un Resolutor
 * (solo `tickets:view_assigned`, spec 038) ya no puede navegar a `/tickets` (vista global,
 * FR-003/FR-004) pero conserva `tickets:create` — este componente es su único punto de
 * entrada para crear un Ticket/Tarea nuevo. Dueño de su propio estado/catálogos, independiente
 * de los filtros de listado de la página que lo monta. */
export default function CreateTicketModal({ onCreated }: { onCreated: () => void }) {
  const { message } = App.useApp()
  const { hasPermission, role } = useAuthStore()
  const canCreate = hasPermission('tickets', 'create')
  const canManageSkills = hasPermission('tickets', 'manage_skills')
  const isEncargado = role?.name === 'Usuario/cliente'

  const [clients, setClients] = useState<ClientListItem[]>([])
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [projectSlaRules, setProjectSlaRules] = useState<SlaRule[]>([])
  const [myProjects, setMyProjects] = useState<ProjectListItem[]>([])
  const [contacts, setContacts] = useState<ClientContact[]>([])
  const [tools, setTools] = useState<CatalogItem[]>([])
  const [processes, setProcesses] = useState<CatalogItem[]>([])
  const [toolProcessLinks, setToolProcessLinks] = useState<ToolProcessLink[]>([])
  const [skills, setSkills] = useState<Skill[]>([])
  const [recordTypes, setRecordTypes] = useState<CatalogItem[]>([])
  const [formOpen, setFormOpen] = useState(false)
  const [taskLists, setTaskLists] = useState<TaskList[]>([])
  const [pendingDescriptionImages, setPendingDescriptionImages] = useState<File[]>([])
  const [descriptionAttachments, setDescriptionAttachments] = useState<UploadFile[]>([])
  const [descriptionKey, setDescriptionKey] = useState(0)
  const [form] = Form.useForm<TicketFormData>()
  const selectedClientId = Form.useWatch('client_id', form)
  const selectedProjectId = Form.useWatch('project_id', form)
  const selectedRecordTypeId = Form.useWatch('record_type_id', form)
  const selectedPriority = Form.useWatch('priority', form)
  const selectedToolId = Form.useWatch('tool_id', form)
  const selectedProcessId = Form.useWatch('process_id', form)
  const isTaskSelected = recordTypes.find(rt => rt.id === selectedRecordTypeId)?.name === 'Tarea'
  const projectRequiredFlow = !isEncargado && !isTaskSelected
  const applicableSlaRule = projectSlaRules.find(r => r.priority === selectedPriority)

  const linkedProcessIds = new Set(
    toolProcessLinks.filter(l => l.tool_id === selectedToolId).map(l => l.process_id))
  const processOptions: DefaultOptionType[] = selectedToolId && linkedProcessIds.size > 0
    ? [
        { label: 'Sugeridos', options: processes.filter(p => linkedProcessIds.has(p.id))
            .map(p => ({ value: p.id, label: p.name })) },
        { label: 'Otros', options: processes.filter(p => !linkedProcessIds.has(p.id))
            .map(p => ({ value: p.id, label: p.name })) },
      ]
    : processes.map(p => ({ value: p.id, label: p.name }))

  const suggestedSkillIds = new Set(
    skills.filter(s => (selectedToolId && s.tool_id === selectedToolId)
      || (selectedProcessId && s.process_id === selectedProcessId)).map(s => s.id))
  const skillOptions: DefaultOptionType[] = suggestedSkillIds.size > 0
    ? [
        { label: 'Sugeridas', options: skills.filter(s => suggestedSkillIds.has(s.id))
            .map(s => ({ value: s.id, label: `${s.code} — ${s.label}` })) },
        { label: 'Otras', options: skills.filter(s => !suggestedSkillIds.has(s.id))
            .map(s => ({ value: s.id, label: `${s.code} — ${s.label}` })) },
      ]
    : skills.map(s => ({ value: s.id, label: `${s.code} — ${s.label}` }))

  useEffect(() => {
    if (!isEncargado) return
    clientContactService.myProjects().then(r => setMyProjects(r.items)).catch(() => undefined)
  }, [isEncargado])

  useEffect(() => {
    if (isEncargado) return
    clientService.list({ active: true, page_size: 100 }).then(r => setClients(r.items))
      .catch(() => message.error('No se pudo cargar la lista de clientes'))
    catalogService.list('tools').then(r => setTools(r.items))
      .catch(() => message.error('No se pudo cargar el catálogo de herramientas'))
    catalogService.list('processes').then(r => setProcesses(r.items))
      .catch(() => message.error('No se pudo cargar el catálogo de procesos'))
    catalogService.listToolProcesses().then(r => setToolProcessLinks(r.items)).catch(() => undefined)
    skillService.list(true).then(r => setSkills(r.items))
      .catch(() => message.error('No se pudo cargar el catálogo de skills'))
    catalogService.list('record-types').then(r => {
      setRecordTypes(r.items)
      const ticketType = r.items.find(rt => rt.name === 'Ticket') ?? r.items[0]
      if (ticketType) form.setFieldValue('record_type_id', ticketType.id)
    }).catch(() => message.error('No se pudo cargar el catálogo de tipo de registro'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEncargado])

  useEffect(() => {
    if (selectedClientId) {
      projectService.list({ client_id: selectedClientId, active: true, page_size: 100 })
        .then(r => setProjects(r.items))
        .catch(() => message.error('No se pudo cargar la lista de proyectos'))
      form.setFieldValue('project_id', undefined)
      form.setFieldValue('client_contact_id', undefined)
    } else {
      setProjects([])
      setContacts([])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedClientId])

  useEffect(() => {
    if (selectedProjectId) {
      taskListService.listByProject(selectedProjectId).then(setTaskLists)
        .catch(() => message.error('No se pudo cargar la lista de Listas del proyecto'))
      clientContactService.list({ project_id: selectedProjectId, page_size: 100, active: true })
        .then(r => setContacts(r.items))
        .catch(() => message.error('No se pudo cargar la lista de usuarios/cliente'))
      form.setFieldValue('list_id', undefined)
      form.setFieldValue('client_contact_id', undefined)
    } else {
      setTaskLists([])
      setContacts([])
      form.setFieldValue('client_contact_id', undefined)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProjectId])

  useEffect(() => {
    if (projectRequiredFlow && selectedProjectId) {
      slaService.list({ project_id: selectedProjectId, page_size: 100 })
        .then(r => setProjectSlaRules(r.items))
        .catch(() => setProjectSlaRules([]))
    } else {
      setProjectSlaRules([])
    }
  }, [projectRequiredFlow, selectedProjectId])

  const handleCreate = async (values: TicketFormData) => {
    try {
      const { skill_ids, ...ticketFields } = values
      const rawAttachments = descriptionAttachments.map(f => f.originFileObj).filter((f): f is NonNullable<typeof f> => !!f)
      const created = await ticketService.create(ticketFields, pendingDescriptionImages, rawAttachments)
      if (canManageSkills && skill_ids?.length) {
        await ticketService.updateTicketSkills(created.id, skill_ids)
      }
      message.success(`Ticket ${created.ticket_number} creado`)
      setFormOpen(false)
      form.resetFields()
      setPendingDescriptionImages([]); setDescriptionAttachments([]); setDescriptionKey(k => k + 1)
      onCreated()
    } catch (err: unknown) {
      if (mapApiErrorToFormFields(err, form, TICKET_ERROR_RULES)) return
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Error al crear el ticket'
      message.error(msg)
    }
  }

  if (!canCreate) return null

  return (
    <>
      <Button type="primary" icon={<PlusOutlined />} onClick={() => {
        form.resetFields()
        setPendingDescriptionImages([]); setDescriptionAttachments([]); setDescriptionKey(k => k + 1)
        const ticketType = recordTypes.find(rt => rt.name === 'Ticket') ?? recordTypes[0]
        if (!isEncargado && ticketType) form.setFieldValue('record_type_id', ticketType.id)
        setFormOpen(true)
      }}>
        Nuevo ticket
      </Button>

      <Modal title="Nuevo ticket" open={formOpen} onCancel={() => setFormOpen(false)}
        onOk={() => form.submit()} okText="Crear ticket" width={isEncargado ? 480 : 760}>
        <Form form={form} layout="vertical" onFinish={handleCreate}
          initialValues={isEncargado ? {} : { ticket_type: 'incident', priority: 'medium', severity: 's3', escalation_level: 'n2' }}>
          <Form.Item name="title" label="Título" rules={TITLE_RULES}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Descripción"
            rules={[{ required: true, message: 'La descripción es requerida' },
              { validator: (_r, v) => (isRichTextEmpty(v || '') ? Promise.reject(new Error('La descripción es requerida')) : Promise.resolve()) }]}>
            <RichTextEditor key={descriptionKey} placeholder="Descripción" allowImages
              onPendingImage={file => setPendingDescriptionImages(prev => [...prev, file])} />
          </Form.Item>
          <Form.Item label="Adjuntos de la descripción">
            <Upload multiple beforeUpload={() => false} fileList={descriptionAttachments}
              onChange={({ fileList }) => setDescriptionAttachments(fileList)}>
              <Button icon={<UploadOutlined />}>Adjuntar (máx 10 MB c/u)</Button>
            </Upload>
          </Form.Item>
          {isEncargado && (
            <Form.Item name="project_id" label="Proyecto (opcional)">
              <Select allowClear disabled={myProjects.length === 0}
                placeholder={myProjects.length === 0 ? 'Sin proyectos vinculados' : 'Proyecto'}
                options={myProjects.map(p => ({ value: p.id, label: p.name }))} />
            </Form.Item>
          )}
          {!isEncargado && <>
            <Form.Item name="record_type_id" label="Tipo de registro"
              rules={[{ required: true, message: 'Selecciona el tipo de registro' }]}>
              <Segmented options={recordTypes.map(rt => ({ value: rt.id, label: rt.name }))} />
            </Form.Item>
            <Space style={{ display: 'flex' }} align="start" wrap>
              <Form.Item name="client_id" label="Cliente" rules={[{ required: true, message: 'El cliente es requerido' }]}>
                <Select showSearch optionFilterProp="label" placeholder="Cliente" style={{ width: 220 }}
                  options={clients.map(c => ({ value: c.id, label: c.name }))} />
              </Form.Item>
              <Form.Item name="project_id" label={projectRequiredFlow ? 'Proyecto' : 'Proyecto (opcional)'}
                rules={projectRequiredFlow ? [{ required: true, message: 'El proyecto es requerido' }] : []}>
                <Select allowClear={!projectRequiredFlow} showSearch optionFilterProp="label"
                  placeholder={selectedClientId ? 'Proyecto' : 'Elige cliente primero'}
                  disabled={!selectedClientId} style={{ width: 220 }}
                  options={projects.map(p => ({ value: p.id, label: p.name }))} />
              </Form.Item>
              <Form.Item name="client_contact_id" label={projectRequiredFlow ? 'Usuario/cliente' : 'Usuario/cliente (opcional)'}
                // spec 038 US4 (FR-018): obligatorio al crear un Ticket (no Tarea) — acotado a
                // cuando el proyecto elegido sí tiene contactos disponibles, para no dejar al
                // usuario sin salida en un proyecto todavía sin ningún Usuario/cliente cargado
                // (mismo criterio ya usado por `project_id`, OBS-0045/spec 033).
                rules={projectRequiredFlow && contacts.length > 0 ? [{ required: true, message: 'El Usuario/cliente solicitante es requerido' }] : []}>
                <Select allowClear placeholder={
                  !selectedProjectId ? 'Elige proyecto primero'
                    : contacts.length === 0 ? 'Sin personal Usuario/cliente en el proyecto' : 'Usuario/cliente'
                } disabled={!selectedProjectId || contacts.length === 0} style={{ width: 220 }}
                  options={contacts.map(c => ({ value: c.id, label: c.username }))} />
              </Form.Item>
              {isTaskSelected && (
                <Form.Item name="list_id" label="Lista (opcional)">
                  <Select allowClear placeholder={selectedProjectId ? 'Lista' : 'Elige proyecto primero'}
                    disabled={!selectedProjectId} style={{ width: 200 }}
                    options={taskLists.map(l => ({ value: l.id, label: l.name }))} />
                </Form.Item>
              )}
            </Space>
            {projectRequiredFlow && selectedProjectId && contacts.length === 0 && (
              <Alert
                type="warning" showIcon style={{ marginBottom: 12 }}
                message="Este proyecto no tiene ningún Usuario/cliente cargado"
                description='Puedes crear el ticket igual (el campo queda sin completar) — agrega un Usuario/cliente en Maestros > Usuarios/cliente para poder asociarlo la próxima vez.'
              />
            )}
            {projectRequiredFlow && selectedProjectId && (
              <Descriptions size="small" column={1} bordered style={{ marginBottom: 12 }}>
                <Descriptions.Item label="Nivel de servicio (SLA)">
                  {applicableSlaRule
                    ? `Contacto: ${applicableSlaRule.contact_minutes} min · Ejecución: ${applicableSlaRule.execution_minutes} min (prioridad ${PRIORITY_LABELS[selectedPriority as Priority] ?? selectedPriority})`
                    : 'Este proyecto/prioridad no tiene una regla de SLA configurada'}
                </Descriptions.Item>
              </Descriptions>
            )}
            <>
              <Space style={{ display: 'flex' }} align="start" wrap>
                <Form.Item name="ticket_type" label="Tipo" rules={isTaskSelected ? [] : [{ required: true }]}>
                  <Select style={{ width: 130 }} options={typeOptions} allowClear={isTaskSelected} />
                </Form.Item>
                <Form.Item name="priority" label="Prioridad" rules={isTaskSelected ? [] : [{ required: true }]}>
                  <Select style={{ width: 110 }} options={priorityOptions} allowClear={isTaskSelected} />
                </Form.Item>
                <Form.Item name="severity" label="Severidad" rules={isTaskSelected ? [] : [{ required: true }]}>
                  <Select style={{ width: 100 }} options={severityOptions} allowClear={isTaskSelected} />
                </Form.Item>
                <Form.Item name="escalation_level" label="Nivel">
                  <Select style={{ width: 90 }} allowClear={isTaskSelected}
                    options={['n1', 'n2', 'n3', 'n4'].map(v => ({ value: v, label: v.toUpperCase() }))} />
                </Form.Item>
              </Space>
              <Space style={{ display: 'flex' }} align="start">
                <Form.Item name="tool_id" label="Herramienta">
                  <Select allowClear placeholder="Herramienta" style={{ width: 200 }}
                    options={tools.map(t => ({ value: t.id, label: t.name }))} />
                </Form.Item>
                <Form.Item name="process_id" label="Proceso">
                  <Select allowClear placeholder="Proceso" style={{ width: 200 }}
                    options={processOptions} />
                </Form.Item>
              </Space>
              <Form.Item name="skill_ids" label="Skills requeridas (opcional)">
                <Select mode="multiple" allowClear disabled={!canManageSkills}
                  placeholder="Sin Skills requeridas" options={skillOptions} />
              </Form.Item>
            </>
          </>}
        </Form>
      </Modal>
    </>
  )
}
