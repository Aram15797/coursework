export type UserRole = "superadmin" | "admin" | "manager" | "member";

export interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string | null;
  avatar_url?: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export type ProjectStatus =
  | "planning"
  | "active"
  | "on_hold"
  | "completed"
  | "archived";

export type ProjectPriority = "low" | "medium" | "high" | "critical";

export interface Project {
  id: string;
  title: string;
  description?: string | null;
  status: ProjectStatus;
  priority: ProjectPriority;
  owner: User;
  start_date?: string | null;
  due_date?: string | null;
  created_at: string;
  updated_at: string;
}

export type ProjectMemberRole = "manager" | "member" | "viewer";

export interface ProjectMember {
  user: User;
  role: ProjectMemberRole;
  joined_at: string;
}

export interface ProjectDetail extends Project {
  members: ProjectMember[];
  task_count: number;
  completed_task_count: number;
  progress: number;
}

export type TaskStatus =
  | "backlog"
  | "todo"
  | "in_progress"
  | "in_review"
  | "done"
  | "cancelled";

export type TaskPriority = "low" | "medium" | "high" | "critical";

export interface Tag {
  id: string;
  name: string;
  color: string;
}

export interface Task {
  id: string;
  title: string;
  description?: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  project_id: string;
  assignee?: User | null;
  reporter: User;
  parent_task_id?: string | null;
  estimated_hours?: number | null;
  logged_hours?: number | null;
  due_date?: string | null;
  position: number;
  tags: Tag[];
  created_at: string;
  updated_at: string;
}

export interface TaskDetail extends Task {
  subtasks: Task[];
}

export interface Comment {
  id: string;
  content: string;
  task_id: string;
  author: User;
  parent_comment_id?: string | null;
  is_edited: boolean;
  created_at: string;
  updated_at: string;
  replies: Comment[];
}

export interface ActivityEntry {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  user_id?: string | null;
  old_values?: Record<string, unknown> | null;
  new_values?: Record<string, unknown> | null;
  created_at: string;
}

export interface QueryLogEntry {
  sql: string;
  operation: "SELECT" | "INSERT" | "UPDATE" | "DELETE" | "OTHER";
  tables: string[];
  duration_ms: number;
  row_count: number | null;
  parameters?: string | null;
  explain?: string | null;
}

export interface QueryLog {
  request_id: string;
  method: string;
  path: string;
  query_count: number;
  total_duration_ms: number;
  n_plus_one_warnings: string[];
  queries: QueryLogEntry[];
}

export interface DbSchemaColumn {
  name: string;
  type: string;
  nullable: boolean;
  default?: string | null;
  max_length?: number | null;
}

export interface DbSchemaForeignKey {
  column: string;
  references_table: string;
  references_column: string;
  name: string;
}

export interface DbSchemaTable {
  name: string;
  columns: DbSchemaColumn[];
  primary_key: string[];
  foreign_keys: DbSchemaForeignKey[];
  unique: string[];
}

export interface DbIndex {
  schema: string;
  table: string;
  name: string;
  definition: string;
}

export interface DbStat {
  table_name: string;
  row_count: number;
  dead_rows: number;
  seq_scan: number;
  idx_scan: number;
  total_size: string;
  size_bytes: number;
}
