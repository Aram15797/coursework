import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { commentsApi, tasksApi } from "@/api/endpoints";
import { formatDateTime } from "@/lib/utils";
import type { TaskStatus } from "@/types";

const STATUSES: TaskStatus[] = [
  "backlog",
  "todo",
  "in_progress",
  "in_review",
  "done",
  "cancelled",
];

export function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const qc = useQueryClient();
  const [comment, setComment] = useState("");

  const task = useQuery({
    queryKey: ["task", taskId],
    queryFn: () => tasksApi.get(taskId!),
    enabled: !!taskId,
  });

  const comments = useQuery({
    queryKey: ["comments", taskId],
    queryFn: () => commentsApi.list(taskId!),
    enabled: !!taskId,
  });

  const updateTask = useMutation({
    mutationFn: (status: TaskStatus) => tasksApi.update(taskId!, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["task", taskId] }),
  });

  const addComment = useMutation({
    mutationFn: () => commentsApi.create(taskId!, comment),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["comments", taskId] });
      setComment("");
    },
  });

  if (!task.data) return <div className="text-slate-500">Loading…</div>;

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <Link to={`/projects/${task.data.project_id}`} className="text-sm text-brand-600 hover:underline">
          ← Back to project
        </Link>
      </div>
      <div className="card p-5 space-y-3">
        <h1 className="text-2xl font-semibold">{task.data.title}</h1>
        <p className="text-slate-600">{task.data.description || "No description"}</p>
        <div className="flex flex-wrap gap-3 text-sm">
          <div>
            <span className="text-slate-500">Status:</span>{" "}
            <select
              className="ml-1 input inline-block w-auto py-1"
              value={task.data.status}
              onChange={(e) => updateTask.mutate(e.target.value as TaskStatus)}
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <span className="text-slate-500">Priority:</span> {task.data.priority}
          </div>
          <div>
            <span className="text-slate-500">Assignee:</span>{" "}
            {task.data.assignee?.username || "—"}
          </div>
          <div>
            <span className="text-slate-500">Reporter:</span> {task.data.reporter.username}
          </div>
          <div>
            <span className="text-slate-500">Due:</span> {task.data.due_date || "—"}
          </div>
        </div>
        {task.data.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {task.data.tags.map((t) => (
              <span
                key={t.id}
                className="badge"
                style={{ background: t.color + "20", color: t.color }}
              >
                {t.name}
              </span>
            ))}
          </div>
        )}
        {task.data.subtasks.length > 0 && (
          <div>
            <h3 className="font-semibold mt-3 mb-2">Subtasks</h3>
            <ul className="space-y-1 text-sm">
              {task.data.subtasks.map((st) => (
                <li key={st.id}>
                  <Link to={`/tasks/${st.id}`} className="text-brand-600 hover:underline">
                    {st.title}
                  </Link>{" "}
                  <span className="text-slate-500 text-xs">({st.status})</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="card p-5">
        <h2 className="font-semibold mb-3">Comments</h2>
        <div className="space-y-3">
          {comments.data?.map((c) => (
            <div key={c.id} className="border-b border-slate-100 pb-2">
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span className="font-medium text-slate-700">
                  {c.author.full_name || c.author.username}
                </span>
                <span>{formatDateTime(c.created_at)}</span>
                {c.is_edited && <span>(edited)</span>}
              </div>
              <div className="text-sm mt-1">{c.content}</div>
            </div>
          ))}
          {!comments.data?.length && (
            <div className="text-sm text-slate-500">No comments yet.</div>
          )}
        </div>
        <div className="mt-4 flex gap-2">
          <input
            className="input flex-1"
            placeholder="Write a comment…"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          <button
            className="btn-primary"
            disabled={!comment || addComment.isPending}
            onClick={() => addComment.mutate()}
          >
            Post
          </button>
        </div>
      </div>
    </div>
  );
}
