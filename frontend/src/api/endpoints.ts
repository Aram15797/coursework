import { api } from "@/api/client";
import type {
  ActivityEntry,
  Comment,
  DbIndex,
  DbSchemaTable,
  DbStat,
  Project,
  ProjectDetail,
  QueryLog,
  Tag,
  Task,
  TaskDetail,
  User,
} from "@/types";

export const authApi = {
  login: (email: string, password: string) =>
    api.post<{ access_token: string; user: User }>("/auth/login", { email, password }).then((r) => r.data),
  register: (data: { email: string; username: string; password: string; full_name?: string }) =>
    api.post<User>("/auth/register", data).then((r) => r.data),
  logout: () => api.post("/auth/logout").then((r) => r.data),
  refresh: () =>
    api.post<{ access_token: string; user: User }>("/auth/refresh").then((r) => r.data),
};

export const usersApi = {
  me: () => api.get<User>("/users/me").then((r) => r.data),
  updateMe: (data: { full_name?: string; username?: string; avatar_url?: string }) =>
    api.patch<User>("/users/me", data).then((r) => r.data),
  changePassword: (old_password: string, new_password: string) =>
    api.post("/users/me/password", { old_password, new_password }),
  list: () => api.get<User[]>("/users").then((r) => r.data),
};

export const projectsApi = {
  list: (params?: { status?: string; priority?: string; search?: string }) =>
    api.get<Project[]>("/projects", { params }).then((r) => r.data),
  get: (id: string) => api.get<ProjectDetail>(`/projects/${id}`).then((r) => r.data),
  create: (data: Partial<Project>) => api.post<Project>("/projects", data).then((r) => r.data),
  update: (id: string, data: Partial<Project>) =>
    api.patch<Project>(`/projects/${id}`, data).then((r) => r.data),
  remove: (id: string) => api.delete(`/projects/${id}`),
  addMember: (id: string, user_id: string, role: string) =>
    api.post(`/projects/${id}/members`, { user_id, role }).then((r) => r.data),
  removeMember: (id: string, user_id: string) =>
    api.delete(`/projects/${id}/members/${user_id}`),
};

export const tasksApi = {
  listByProject: (projectId: string, params?: Record<string, string>) =>
    api.get<Task[]>(`/projects/${projectId}/tasks`, { params }).then((r) => r.data),
  get: (id: string) => api.get<TaskDetail>(`/tasks/${id}`).then((r) => r.data),
  create: (projectId: string, data: Partial<Task> & { tag_ids?: string[] }) =>
    api.post<Task>(`/projects/${projectId}/tasks`, data).then((r) => r.data),
  update: (id: string, data: Partial<Task> & { tag_ids?: string[] }) =>
    api.patch<Task>(`/tasks/${id}`, data).then((r) => r.data),
  move: (id: string, status: string, position: number) =>
    api.patch<Task>(`/tasks/${id}/move`, { status, position }).then((r) => r.data),
  remove: (id: string) => api.delete(`/tasks/${id}`),
};

export const commentsApi = {
  list: (taskId: string) =>
    api.get<Comment[]>(`/tasks/${taskId}/comments`).then((r) => r.data),
  create: (taskId: string, content: string, parent_comment_id?: string) =>
    api
      .post<Comment>(`/tasks/${taskId}/comments`, { content, parent_comment_id })
      .then((r) => r.data),
  update: (id: string, content: string) =>
    api.patch<Comment>(`/comments/${id}`, { content }).then((r) => r.data),
  remove: (id: string) => api.delete(`/comments/${id}`),
};

export const tagsApi = {
  list: () => api.get<Tag[]>("/tags").then((r) => r.data),
  create: (name: string, color: string) =>
    api.post<Tag>("/tags", { name, color }).then((r) => r.data),
};

export const dashboardApi = {
  myTasks: () => api.get<Task[]>("/dashboard/my-tasks").then((r) => r.data),
  stats: () =>
    api
      .get<{
        tasks_by_status: Record<string, number>;
        projects_by_priority: Record<string, number>;
        total_projects: number;
        total_tasks: number;
      }>("/dashboard/stats")
      .then((r) => r.data),
  activity: (limit = 30) =>
    api.get<ActivityEntry[]>("/dashboard/activity", { params: { limit } }).then((r) => r.data),
};

export const dbApi = {
  schema: () => api.get<{ tables: DbSchemaTable[] }>("/db/schema").then((r) => r.data),
  indexes: () => api.get<{ indexes: DbIndex[] }>("/db/indexes").then((r) => r.data),
  stats: () => api.get<{ tables: DbStat[] }>("/db/stats").then((r) => r.data),
  queryLog: (requestId: string) =>
    api.get<QueryLog>(`/db/query-log/${requestId}`).then((r) => r.data),
};
