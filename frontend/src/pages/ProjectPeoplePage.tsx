import { useCallback, useEffect, useMemo, useState } from 'react'
import { Button, Empty, Input, Modal, Select, Space, Spin, Table, Tabs, Tag, Tooltip, message } from 'antd'
import { DeleteOutlined, EditOutlined, PlusOutlined, TeamOutlined, UserAddOutlined } from '@ant-design/icons'
import { useParams } from 'react-router-dom'
import { projectService } from '../services/projectService'
import { projectMemberService } from '../services/projectMemberService'
import { userService } from '../services/userService'
import ConfirmationModal from '../components/common/ConfirmationModal'
import { useAuthStore } from '../store/authStore'
import type { ProjectListItem } from '../types/project'
import type { ProjectMember, ProjectTeam } from '../types/projectMember'
import type { UserAdmin } from '../types/user'
import { avatarColor, initials, palette } from '../theme'

const ROLE_TAG_COLOR: Record<string, string> = {
  Admin: 'gold',
  Coordinador: 'geekblue',
  QM: 'purple',
  Resolutor: 'green',
  'Usuario/cliente': 'orange',
}

/** Personal del Proyecto con pestañas Personas / Equipos, estilo Teamwork (spec 010, US3).
 * Mutaciones solo para roles con permiso de gestión del módulo projects (FR-012). */
export default function ProjectPeoplePage() {
  const { projectId } = useParams<{ projectId: string }>()
  const hasPermission = useAuthStore(s => s.hasPermission)
  const canManage = hasPermission('projects', 'edit')

  const [project, setProject] = useState<ProjectListItem | null>(null)
  const [members, setMembers] = useState<ProjectMember[]>([])
  const [teams, setTeams] = useState<ProjectTeam[]>([])
  const [users, setUsers] = useState<UserAdmin[]>([])
  const [loading, setLoading] = useState(true)

  const [assignOpen, setAssignOpen] = useState(false)
  const [assignUserId, setAssignUserId] = useState<string | undefined>()
  const [removing, setRemoving] = useState<ProjectMember | null>(null)
  const [teamModal, setTeamModal] = useState<{ id?: string; name: string } | null>(null)
  const [deletingTeam, setDeletingTeam] = useState<ProjectTeam | null>(null)
  const [editingMembersTeam, setEditingMembersTeam] = useState<ProjectTeam | null>(null)
  const [teamMemberIds, setTeamMemberIds] = useState<string[]>([])
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    if (!projectId) return
    try {
      const [m, t] = await Promise.all([
        projectMemberService.listMembers(projectId),
        projectMemberService.listTeams(projectId),
      ])
      setMembers(m.items)
      setTeams(t.items)
    } catch {
      message.error('No se pudo cargar el personal del proyecto')
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    if (!projectId) return
    projectService.get(projectId).then(setProject)
      .catch(() => message.error('No se pudo cargar el proyecto'))
    userService.list({ page_size: 100, active: true }).then(r => setUsers(r.items)).catch(() => undefined)
  }, [projectId])

  useEffect(() => { load() }, [load])

  const assignableUsers = useMemo(() => {
    const assigned = new Set(members.map(m => m.user_id))
    return users.filter(u => !assigned.has(u.id))
  }, [users, members])

  const withApiError = (fallback: string) => (err: unknown) => {
    const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? fallback
    message.error(msg)
  }

  const assign = async () => {
    if (!projectId || !assignUserId) {
      message.warning('Elegí un usuario')
      return
    }
    setSaving(true)
    try {
      await projectMemberService.addMember(projectId, assignUserId)
      message.success('Persona asignada al proyecto')
      setAssignOpen(false)
      setAssignUserId(undefined)
      load()
    } catch (err) {
      withApiError('No se pudo asignar')(err)
    } finally {
      setSaving(false)
    }
  }

  const removeMember = async () => {
    if (!projectId || !removing) return
    try {
      await projectMemberService.removeMember(projectId, removing.id)
      message.success('Persona desasignada del proyecto')
      setRemoving(null)
      load()
    } catch (err) {
      withApiError('No se pudo desasignar')(err)
    }
  }

  const saveTeam = async () => {
    if (!projectId || !teamModal) return
    if (!teamModal.name.trim()) {
      message.warning('El nombre es obligatorio')
      return
    }
    setSaving(true)
    try {
      if (teamModal.id) await projectMemberService.renameTeam(teamModal.id, teamModal.name.trim())
      else await projectMemberService.createTeam(projectId, teamModal.name.trim())
      message.success(teamModal.id ? 'Equipo renombrado' : 'Equipo creado')
      setTeamModal(null)
      load()
    } catch (err) {
      withApiError('No se pudo guardar el equipo')(err)
    } finally {
      setSaving(false)
    }
  }

  const deleteTeam = async () => {
    if (!deletingTeam) return
    try {
      await projectMemberService.deleteTeam(deletingTeam.id)
      message.success('Equipo eliminado — sus miembros siguen asignados al proyecto')
      setDeletingTeam(null)
      load()
    } catch (err) {
      withApiError('No se pudo eliminar el equipo')(err)
    }
  }

  const saveTeamMembers = async () => {
    if (!editingMembersTeam) return
    setSaving(true)
    try {
      await projectMemberService.setTeamMembers(editingMembersTeam.id, teamMemberIds)
      message.success('Miembros actualizados')
      setEditingMembersTeam(null)
      load()
    } catch (err) {
      withApiError('No se pudieron actualizar los miembros')(err)
    } finally {
      setSaving(false)
    }
  }

  if (!project || loading) return <Spin style={{ display: 'block', margin: '80px auto' }} />

  const memberColumns = [
    {
      title: 'Nombre', dataIndex: 'full_name', key: 'full_name',
      render: (_: unknown, m: ProjectMember) => (
        <Space>
          <div style={{
            width: 28, height: 28, borderRadius: '50%', display: 'flex', alignItems: 'center',
            justifyContent: 'center', background: avatarColor(m.user_id).bg,
            color: avatarColor(m.user_id).text, fontSize: 11, fontWeight: 700,
          }}>
            {initials(m.full_name ?? '?')}
          </div>
          <span>{m.full_name}</span>
        </Space>
      ),
    },
    { title: 'Correo electrónico', dataIndex: 'email', key: 'email' },
    {
      title: 'Tipo', dataIndex: 'role_name', key: 'role_name',
      render: (role: string | null) => role
        ? <Tag color={ROLE_TAG_COLOR[role] ?? 'default'}>{role}</Tag> : '—',
    },
    {
      title: 'Fecha añadida', dataIndex: 'assigned_at', key: 'assigned_at',
      render: (v: string | null) => v ? new Date(v).toLocaleDateString() : '—',
    },
    ...(canManage ? [{
      title: '', key: 'actions',
      render: (_: unknown, m: ProjectMember) => (
        <Tooltip title="Quitar del proyecto">
          <Button danger type="text" size="small" icon={<DeleteOutlined />}
            onClick={() => setRemoving(m)} />
        </Tooltip>
      ),
    }] : []),
  ]

  const peopleTab = (
    <>
      {canManage && (
        <Button type="primary" icon={<UserAddOutlined />} style={{ marginBottom: 12 }}
          onClick={() => setAssignOpen(true)}>
          Asignar personal
        </Button>
      )}
      <Table rowKey="id" dataSource={members} columns={memberColumns} pagination={false}
        locale={{ emptyText: 'Sin personal asignado todavía.' }} size="middle" />
    </>
  )

  const teamsTab = (
    <>
      {canManage && (
        <Button type="primary" icon={<PlusOutlined />} style={{ marginBottom: 12 }}
          onClick={() => setTeamModal({ name: '' })}>
          Agregar equipo
        </Button>
      )}
      {teams.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Sin equipos todavía." />
      ) : teams.map(team => (
        <div key={team.id} style={{
          display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px',
          border: `1px solid ${palette.slate200}`, borderRadius: 8, marginBottom: 8,
        }}>
          <TeamOutlined style={{ fontSize: 18, color: palette.slate400 }} />
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, fontSize: 13 }}>{team.name}</div>
            <div style={{ fontSize: 12, color: palette.slate500 }}>
              {team.member_count} miembro{team.member_count === 1 ? '' : 's'}
            </div>
          </div>
          <div style={{ display: 'flex' }}>
            {team.members.slice(0, 6).map(m => (
              <Tooltip key={m.member_id} title={m.full_name}>
                <div style={{
                  width: 26, height: 26, borderRadius: '50%', display: 'flex', alignItems: 'center',
                  justifyContent: 'center', background: avatarColor(m.user_id).bg,
                  color: avatarColor(m.user_id).text, fontSize: 10, fontWeight: 700,
                  marginLeft: -6, border: '2px solid #fff',
                }}>
                  {initials(m.full_name ?? '?')}
                </div>
              </Tooltip>
            ))}
            {team.member_count > 6 && (
              <div style={{
                width: 26, height: 26, borderRadius: '50%', display: 'flex', alignItems: 'center',
                justifyContent: 'center', background: palette.slate200, fontSize: 10,
                fontWeight: 700, marginLeft: -6, border: '2px solid #fff',
              }}>
                +{team.member_count - 6}
              </div>
            )}
          </div>
          {canManage && (
            <Space>
              <Tooltip title="Administrar miembros">
                <Button type="text" size="small" icon={<UserAddOutlined />}
                  onClick={() => {
                    setEditingMembersTeam(team)
                    setTeamMemberIds(team.members.map(m => m.member_id))
                  }} />
              </Tooltip>
              <Tooltip title="Renombrar">
                <Button type="text" size="small" icon={<EditOutlined />}
                  onClick={() => setTeamModal({ id: team.id, name: team.name })} />
              </Tooltip>
              <Tooltip title="Eliminar equipo">
                <Button danger type="text" size="small" icon={<DeleteOutlined />}
                  onClick={() => setDeletingTeam(team)} />
              </Tooltip>
            </Space>
          )}
        </div>
      ))}
    </>
  )

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>{project.name}</h2>
        <span style={{ color: palette.slate500, fontSize: 13 }}>› Personal</span>
      </div>

      <Tabs
        items={[
          { key: 'people', label: `Personas (${members.length})`, children: peopleTab },
          { key: 'teams', label: `Equipos (${teams.length})`, children: teamsTab },
        ]}
      />

      <Modal title="Asignar personal" open={assignOpen} confirmLoading={saving}
        onCancel={() => setAssignOpen(false)} onOk={assign} okText="Asignar">
        <Select showSearch allowClear style={{ width: '100%' }} value={assignUserId}
          placeholder="Buscar usuario por nombre o correo" onChange={setAssignUserId}
          optionFilterProp="label"
          options={assignableUsers.map(u => ({
            value: u.id,
            label: `${u.username} · ${u.email} (${u.role.name})`,
          }))} />
      </Modal>

      <Modal title={teamModal?.id ? 'Renombrar equipo' : 'Nuevo equipo'} open={!!teamModal}
        confirmLoading={saving} onCancel={() => setTeamModal(null)} onOk={saveTeam}
        okText="Guardar">
        <Input placeholder="p. ej. Infraestructura" value={teamModal?.name ?? ''}
          onChange={e => setTeamModal(prev => prev ? { ...prev, name: e.target.value } : prev)}
          autoFocus />
      </Modal>

      <Modal title={`Miembros de "${editingMembersTeam?.name ?? ''}"`}
        open={!!editingMembersTeam} confirmLoading={saving}
        onCancel={() => setEditingMembersTeam(null)} onOk={saveTeamMembers} okText="Guardar">
        <Select mode="multiple" style={{ width: '100%' }} value={teamMemberIds}
          placeholder="Personal asignado del proyecto" onChange={setTeamMemberIds}
          optionFilterProp="label"
          options={members.map(m => ({ value: m.id, label: `${m.full_name} (${m.role_name})` }))} />
      </Modal>

      <ConfirmationModal
        open={!!removing}
        title="Quitar del proyecto"
        description={`¿Quitar a "${removing?.full_name}" del personal del proyecto? Saldrá también de todos los equipos. Sus registros históricos (tickets, tiempos) no se ven afectados.`}
        onConfirm={removeMember}
        onCancel={() => setRemoving(null)}
      />

      <ConfirmationModal
        open={!!deletingTeam}
        title="Eliminar equipo"
        description={`¿Eliminar el equipo "${deletingTeam?.name}"? Sus miembros seguirán asignados al proyecto.`}
        onConfirm={deleteTeam}
        onCancel={() => setDeletingTeam(null)}
      />
    </div>
  )
}
