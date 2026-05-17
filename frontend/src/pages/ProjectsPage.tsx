import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { projectsApi } from "@/api/endpoints";
import { formatDate } from "@/lib/utils";

const STATUS_BADGE: Record<string, string> = {
  planning: "bg-slate-100 text-slate-700",
  active: "bg-emerald-100 text-emerald-700",
  on_hold: "bg-amber-100 text-amber-700",
  completed: "bg-blue-100 text-blue-700",
  archived: "bg-slate-200 text-slate-600",
};

const PRIORITY_BADGE: Record<string, string> = {
  low: "bg-slate-100 text-slate-600",
  medium: "bg-blue-100 text-blue-700",
  high: "bg-orange-100 text-orange-700",
  critical: "bg-red-100 text-red-700",
};

export function ProjectsPage() {
  const qc = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list(),
  });

  const createMutation = useMutation({
    mutationFn: () => projectsApi.create({ title, description }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      setCreating(false);
      setTitle("");
      setDescription("");
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <button onClick={() => setCreating(true)} className="btn-primary">
          <Plus className="h-4 w-4" />
          New Project
        </button>
      </div>

      {creating && (
        <div className="card p-4 space-y-3">
          <h2 className="font-semibold">Create new project</h2>
          <div>
            <label className="label">Title</label>
            <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div>
            <label className="label">Description</label>
            <textarea
              className="input min-h-[80px]"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <button
              className="btn-primary"
              onClick={() => createMutation.mutate()}
              disabled={!title || createMutation.isPending}
            >
              Create
            </button>
            <button className="btn-secondary" onClick={() => setCreating(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-slate-500">Loading…</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {projects.map((p) => (
            <Link
              key={p.id}
              to={`/projects/${p.id}`}
              className="card p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold">{p.title}</h3>
                <span className={`badge ${PRIORITY_BADGE[p.priority]}`}>{p.priority}</span>
              </div>
              <p className="text-sm text-slate-600 line-clamp-2 mb-3">
                {p.description || "No description"}
              </p>
              <div className="flex items-center justify-between text-xs">
                <span className={`badge ${STATUS_BADGE[p.status]}`}>{p.status}</span>
                <span className="text-slate-500">
                  {p.due_date ? `Due ${formatDate(p.due_date)}` : ""}
                </span>
              </div>
            </Link>
          ))}
          {!projects.length && (
            <div className="text-slate-500 col-span-full">No projects yet.</div>
          )}
        </div>
      )}
    </div>
  );
}
