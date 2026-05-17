import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { projectsApi, tasksApi } from "@/api/endpoints";
import type { Task, TaskStatus } from "@/types";

const COLUMNS: { key: TaskStatus; title: string }[] = [
  { key: "backlog", title: "Backlog" },
  { key: "todo", title: "To Do" },
  { key: "in_progress", title: "In Progress" },
  { key: "in_review", title: "In Review" },
  { key: "done", title: "Done" },
];

const PRIORITY_COLOR: Record<string, string> = {
  low: "border-slate-300",
  medium: "border-blue-400",
  high: "border-orange-400",
  critical: "border-red-500",
};

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const qc = useQueryClient();
  const [view, setView] = useState<"kanban" | "list">("kanban");
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");

  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  });

  const tasks = useQuery({
    queryKey: ["tasks", projectId],
    queryFn: () => tasksApi.listByProject(projectId!),
    enabled: !!projectId,
  });

  const createTask = useMutation({
    mutationFn: () => tasksApi.create(projectId!, { title: newTitle }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks", projectId] });
      qc.invalidateQueries({ queryKey: ["project", projectId] });
      setNewTitle("");
      setCreating(false);
    },
  });

  const moveTask = useMutation({
    mutationFn: ({ id, status }: { id: string; status: TaskStatus }) =>
      tasksApi.move(id, status, 0),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks", projectId] }),
  });

  const tasksByStatus = COLUMNS.reduce<Record<string, Task[]>>((acc, col) => {
    acc[col.key] = (tasks.data || []).filter((t) => t.status === col.key);
    return acc;
  }, {});

  const onDragStart = (e: React.DragEvent, taskId: string) => {
    e.dataTransfer.setData("text/plain", taskId);
  };
  const onDrop = (e: React.DragEvent, status: TaskStatus) => {
    const id = e.dataTransfer.getData("text/plain");
    if (id) moveTask.mutate({ id, status });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{project.data?.title || "Project"}</h1>
          <p className="text-slate-600 text-sm">{project.data?.description}</p>
          {project.data && (
            <div className="text-xs text-slate-500 mt-1">
              Progress: {project.data.progress}% · {project.data.completed_task_count}/
              {project.data.task_count} tasks · Status: {project.data.status}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-md ring-1 ring-slate-300 overflow-hidden text-sm">
            <button
              className={`px-3 py-1.5 ${view === "kanban" ? "bg-brand-600 text-white" : "bg-white"}`}
              onClick={() => setView("kanban")}
            >
              Kanban
            </button>
            <button
              className={`px-3 py-1.5 ${view === "list" ? "bg-brand-600 text-white" : "bg-white"}`}
              onClick={() => setView("list")}
            >
              List
            </button>
          </div>
          <button onClick={() => setCreating(true)} className="btn-primary">
            <Plus className="h-4 w-4" />
            New Task
          </button>
        </div>
      </div>

      {creating && (
        <div className="card p-3 flex gap-2">
          <input
            className="input flex-1"
            placeholder="Task title…"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
          />
          <button
            className="btn-primary"
            disabled={!newTitle || createTask.isPending}
            onClick={() => createTask.mutate()}
          >
            Add
          </button>
          <button className="btn-secondary" onClick={() => setCreating(false)}>
            Cancel
          </button>
        </div>
      )}

      {view === "kanban" ? (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {COLUMNS.map((col) => (
            <div
              key={col.key}
              className="bg-slate-100 rounded-lg p-3 min-h-[400px]"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => onDrop(e, col.key)}
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-sm text-slate-700">{col.title}</h3>
                <span className="text-xs text-slate-500">
                  {tasksByStatus[col.key]?.length || 0}
                </span>
              </div>
              <div className="space-y-2">
                {tasksByStatus[col.key]?.map((t) => (
                  <Link
                    key={t.id}
                    to={`/tasks/${t.id}`}
                    draggable
                    onDragStart={(e) => onDragStart(e, t.id)}
                    className={`block bg-white rounded-md p-3 shadow-sm border-l-4 ${PRIORITY_COLOR[t.priority]} hover:shadow-md transition-shadow`}
                  >
                    <div className="text-sm font-medium">{t.title}</div>
                    <div className="text-xs text-slate-500 mt-1">
                      {t.assignee?.username || "Unassigned"}
                    </div>
                    {t.tags.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {t.tags.map((tag) => (
                          <span
                            key={tag.id}
                            className="text-[10px] px-1.5 py-0.5 rounded"
                            style={{ background: tag.color + "20", color: tag.color }}
                          >
                            {tag.name}
                          </span>
                        ))}
                      </div>
                    )}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Title</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Priority</th>
                <th className="px-3 py-2">Assignee</th>
                <th className="px-3 py-2">Due</th>
              </tr>
            </thead>
            <tbody>
              {tasks.data?.map((t) => (
                <tr key={t.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-3 py-2">
                    <Link to={`/tasks/${t.id}`} className="text-brand-700 hover:underline">
                      {t.title}
                    </Link>
                  </td>
                  <td className="px-3 py-2">{t.status}</td>
                  <td className="px-3 py-2">{t.priority}</td>
                  <td className="px-3 py-2">{t.assignee?.username || "—"}</td>
                  <td className="px-3 py-2">{t.due_date || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
