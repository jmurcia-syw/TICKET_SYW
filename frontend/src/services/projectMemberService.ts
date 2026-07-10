import apiClient from './apiClient'
import type { ProjectMember, ProjectTeam } from '../types/projectMember'

interface ListResponse<T> {
  items: T[]
  total: number
}

export const projectMemberService = {
  listMembers: (projectId: string, roleName?: string) =>
    apiClient
      .get<ListResponse<ProjectMember>>(`/api/projects/${projectId}/members`, {
        params: roleName ? { role_name: roleName } : undefined,
      })
      .then(r => r.data),

  addMember: (projectId: string, userId: string) =>
    apiClient
      .post<ProjectMember>(`/api/projects/${projectId}/members`, { user_id: userId })
      .then(r => r.data),

  removeMember: (projectId: string, memberId: string) =>
    apiClient.delete(`/api/projects/${projectId}/members/${memberId}`).then(() => undefined),

  listTeams: (projectId: string) =>
    apiClient.get<ListResponse<ProjectTeam>>(`/api/projects/${projectId}/teams`).then(r => r.data),

  createTeam: (projectId: string, name: string) =>
    apiClient.post<ProjectTeam>(`/api/projects/${projectId}/teams`, { name }).then(r => r.data),

  renameTeam: (teamId: string, name: string) =>
    apiClient.patch<ProjectTeam>(`/api/project-teams/${teamId}`, { name }).then(r => r.data),

  deleteTeam: (teamId: string) =>
    apiClient.delete(`/api/project-teams/${teamId}`).then(() => undefined),

  setTeamMembers: (teamId: string, memberIds: string[]) =>
    apiClient
      .put<ProjectTeam>(`/api/project-teams/${teamId}/members`, { member_ids: memberIds })
      .then(r => r.data),
}
