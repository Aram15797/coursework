import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { dashboardApi } from "@/api/endpoints";
import { formatDateTime } from "@/lib/utils";

const STATUS_COLORS: Record<string, string> = {
  backlog: "#94a3b8",
  todo: "#60a5fa",
  in_progress: "#fbbf24",
  in_review: "#a78bfa",
  done: "#34d399",
  cancelled: "#f87171",
};

const PRIORITY_COLORS: Record<string, string> = {
  low: "#94a3b8",
  medium: "#60a5fa",
  high: "#fb923c",
  critical: "#ef4444",
};

export function DashboardPage() {
  const stats = useQuery({ queryKey: ["dashboard-stats"], queryFn: dashboardApi.stats });
  const myTasks = useQuery({ queryKey: ["my-tasks"], queryFn: dashboardApi.myTasks });
  const activity = useQuery({ queryKey: ["activity"], queryFn: () => dashboardApi.activity(20) });

  const statusData = Object.entries(stats.data?.tasks_by_status || {}).map(([k, v]) => ({
    name: k,
    value: v,
  }));
  const priorityData = Object.entries(stats.data?.projects_by_priority || {}).map(
    ([k, v]) => ({ name: k, value: v }),
  );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <div className="text-sm text-slate-500">Total Projects</div>
          <div className="text-2xl font-bold">{stats.data?.total_projects ?? "—"}</div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-slate-500">Total Tasks</div>
          <div className="text-2xl font-bold">{stats.data?.total_tasks ?? "—"}</div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-slate-500">My Open Tasks</div>
          <div className="text-2xl font-bold">{myTasks.data?.length ?? "—"}</div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-slate-500">Recent Activity</div>
          <div className="text-2xl font-bold">{activity.data?.length ?? "—"}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-4">
          <h2 className="font-semibold mb-3">Tasks by Status</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={statusData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="value">
                {statusData.map((d, i) => (
                  <Cell key={i} fill={STATUS_COLORS[d.name] || "#6366f1"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-4">
          <h2 className="font-semibold mb-3">Projects by Priority</h2>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={priorityData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={90}
                label
              >
                {priorityData.map((d, i) => (
                  <Cell key={i} fill={PRIORITY_COLORS[d.name] || "#6366f1"} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-4">
          <h2 className="font-semibold mb-3">My Tasks</h2>
          <div className="space-y-2">
            {myTasks.data?.length ? (
              myTasks.data.map((t) => (
                <div
                  key={t.id}
                  className="flex justify-between items-center border-b border-slate-100 pb-2"
                >
                  <div>
                    <div className="font-medium text-sm">{t.title}</div>
                    <div className="text-xs text-slate-500">
                      {t.status} · {t.priority}
                    </div>
                  </div>
                  <div className="text-xs text-slate-500">
                    {t.due_date ? `Due ${t.due_date}` : ""}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-500">No open tasks.</div>
            )}
          </div>
        </div>

        <div className="card p-4">
          <h2 className="font-semibold mb-3">Recent Activity</h2>
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {activity.data?.map((a) => (
              <div key={a.id} className="text-sm border-b border-slate-100 pb-2">
                <span className="font-medium">{a.action}</span>{" "}
                <span className="text-slate-500">{a.entity_type}</span>{" "}
                <span className="text-xs text-slate-400">
                  {formatDateTime(a.created_at)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
