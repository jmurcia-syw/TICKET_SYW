import apiClient from './apiClient'
import type { TaskList } from '../types/taskList'

export const taskListService = {
  listByProject: (projectId: string) =>
    apiClient.get<{ items: TaskList[] }>(`/api/projects/${projectId}/task-lists`).then(r => r.data.items),

  create: (projectId: string, name: string) =>
    apiClient.post<TaskList>(`/api/projects/${projectId}/task-lists`, { name }).then(r => r.data),

  update: (id: string, data: { name?: string; position?: number }) =>
    apiClient.patch<TaskList>(`/api/task-lists/${id}`, data).then(r => r.data),
}
