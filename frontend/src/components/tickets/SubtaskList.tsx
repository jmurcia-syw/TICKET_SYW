import { useEffect, useState } from 'react'
import { Button, Empty, Input, Modal, Select, Space, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { TicketDetail } from '../../types/ticket'
import { STATUS_LABELS } from '../../types/ticket'
import { ticketService } from '../../services/ticketService'
import { resourceService } from '../../services/resourceService'
import type { Resource } from '../../types/resource'
import { avatarColor, initials, palette, TICKET_STATUS_CHIP } from '../../theme'

interface SubtaskListProps {
  ticket: TicketDetail
  onUpdated: () => void
}

/** Subtareas (Nivel 5) anidadas bajo una Tarea, con Encargado y estado propios — según
 * `docs/mockup.html` (filas indentadas con avatar y badge de estado). Spec 009, US4. */
export default function SubtaskList({ ticket, onUpdated }: SubtaskListProps) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [assigneeId, setAssigneeId] = useState<string | undefined>()
  const [resources, setResources] = useState<Resource[]>([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open) {
      resourceService.list({ active: true, page_size: 100 }).then(r => setResources(r.items))
        .catch(() => message.error('No se pudo cargar la lista de recursos'))
    }
  }, [open])

  const create = async () => {
    if (!title.trim()) {
      message.warning('El título es obligatorio')
      return
    }
    setSaving(true)
    try {
      await ticketService.create({
        title: title.trim(), description: description.trim() || 'Subtarea',
        client_id: ticket.client?.id, project_id: ticket.project?.id,
        record_type_id: ticket.record_type_id,
        parent_task_id: ticket.id,
        assignee_id: assigneeId,
      })
      message.success('Subtarea creada')
      setOpen(false); setTitle(''); setDescription(''); setAssigneeId(undefined)
      onUpdated()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'No se pudo crear la subtarea'
      message.error(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      {ticket.subtasks.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={<span style={{ fontSize: 12, color: palette.slate400 }}>Sin subtareas</span>}
          style={{ margin: '8px 0' }} />
      ) : (
        <Space direction="vertical" size={6} style={{ width: '100%' }}>
          {ticket.subtasks.map(s => {
            const chip = TICKET_STATUS_CHIP[s.status]
            return (
              <div key={s.id}
                onClick={() => navigate(`/tickets/${s.id}`)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer',
                  padding: '6px 8px', borderRadius: 6, border: `1px solid ${palette.slate200}`,
                }}
              >
                <span style={{ color: palette.slate400, fontSize: 12 }}>└</span>
                {s.assignee ? (
                  <div style={{
                    width: 18, height: 18, borderRadius: '50%', display: 'flex', alignItems: 'center',
                    justifyContent: 'center', background: avatarColor(s.assignee.id).bg,
                    color: avatarColor(s.assignee.id).text, fontSize: 8, fontWeight: 700, flexShrink: 0,
                  }}>
                    {initials(s.assignee.full_name)}
                  </div>
                ) : null}
                <span style={{ fontSize: 12, flex: 1 }}>{s.title}</span>
                <span style={{
                  fontSize: 11, fontWeight: 600, padding: '1px 8px', borderRadius: 999,
                  background: chip?.bg, color: chip?.text,
                }}>
                  {STATUS_LABELS[s.status]}
                </span>
              </div>
            )
          })}
        </Space>
      )}

      <Button type="link" size="small" icon={<PlusOutlined />} style={{ padding: '8px 0 0' }}
        onClick={() => setOpen(true)}>
        Agregar subtarea
      </Button>

      <Modal title="Nueva subtarea" open={open} onCancel={() => setOpen(false)}
        confirmLoading={saving} onOk={create} okText="Crear">
        <Space direction="vertical" style={{ width: '100%' }}>
          <Input placeholder="Título" value={title} onChange={e => setTitle(e.target.value)} autoFocus />
          <Input.TextArea rows={3} placeholder="Descripción (opcional)" value={description}
            onChange={e => setDescription(e.target.value)} />
          <Select placeholder="Encargado (opcional, default: vos)" allowClear showSearch
            optionFilterProp="label" style={{ width: '100%' }}
            value={assigneeId} onChange={setAssigneeId}
            options={resources.map(r => ({ value: r.id, label: r.full_name }))} />
        </Space>
      </Modal>
    </div>
  )
}
