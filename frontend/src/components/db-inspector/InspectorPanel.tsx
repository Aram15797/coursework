import { AlertTriangle, ChevronDown, ChevronUp, Trash2, X } from "lucide-react";
import Prism from "prismjs";
import "prismjs/components/prism-sql";
import { useEffect, useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useInspectorStore } from "@/store/inspector-store";

const OP_COLOR: Record<string, string> = {
  SELECT: "bg-blue-100 text-blue-700",
  INSERT: "bg-emerald-100 text-emerald-700",
  UPDATE: "bg-amber-100 text-amber-700",
  DELETE: "bg-red-100 text-red-700",
  OTHER: "bg-slate-100 text-slate-700",
};

export function InspectorPanel() {
  const { enabled, open, logs, selectedRequestId, setOpen, selectRequest, clear } =
    useInspectorStore();

  const selected = useMemo(
    () => logs.find((l) => l.request_id === selectedRequestId) || logs[0],
    [logs, selectedRequestId],
  );

  useEffect(() => {
    if (open) Prism.highlightAll();
  }, [open, selected]);

  if (!enabled) return null;

  return (
    <div className="border-t border-slate-200 bg-white">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
      >
        <span className="font-semibold">
          DB Inspector{" "}
          {selected && (
            <span className="text-slate-500">
              · {selected.method} {selected.path} · {selected.query_count} queries ·{" "}
              {selected.total_duration_ms}ms
            </span>
          )}
        </span>
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
      </button>
      {open && (
        <div className="grid grid-cols-12 h-[40vh] overflow-hidden">
          <div className="col-span-3 border-r border-slate-200 overflow-y-auto">
            <div className="flex justify-between items-center px-3 py-2 border-b border-slate-100">
              <span className="text-xs font-semibold text-slate-500">REQUESTS</span>
              <button onClick={clear} className="text-slate-400 hover:text-red-600">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
            {logs.map((l) => (
              <button
                key={l.request_id}
                onClick={() => selectRequest(l.request_id)}
                className={`w-full text-left px-3 py-2 border-b border-slate-100 hover:bg-slate-50 ${
                  selected?.request_id === l.request_id ? "bg-brand-50" : ""
                }`}
              >
                <div className="text-xs font-mono text-slate-700 truncate">
                  {l.method} {l.path}
                </div>
                <div className="text-[11px] text-slate-500">
                  {l.query_count} · {l.total_duration_ms}ms
                  {l.n_plus_one_warnings.length > 0 && (
                    <span className="text-amber-600 ml-1">⚠</span>
                  )}
                </div>
              </button>
            ))}
            {!logs.length && (
              <div className="p-3 text-xs text-slate-500">
                Make a request to see queries.
              </div>
            )}
          </div>
          <div className="col-span-9 overflow-y-auto p-3 space-y-3">
            {selected ? (
              <>
                <div className="flex gap-4 text-xs">
                  <div className="card px-3 py-2">
                    <div className="text-slate-500">Queries</div>
                    <div className="font-bold">{selected.query_count}</div>
                  </div>
                  <div className="card px-3 py-2">
                    <div className="text-slate-500">Total time</div>
                    <div className="font-bold">{selected.total_duration_ms}ms</div>
                  </div>
                  <div className="card px-3 py-2">
                    <div className="text-slate-500">Path</div>
                    <div className="font-mono text-[11px]">{selected.path}</div>
                  </div>
                </div>

                {selected.n_plus_one_warnings.length > 0 && (
                  <div className="bg-amber-50 border border-amber-200 rounded-md p-2 text-xs text-amber-800 flex gap-2">
                    <AlertTriangle className="h-4 w-4 shrink-0" />
                    <div>
                      {selected.n_plus_one_warnings.map((w, i) => (
                        <div key={i}>{w}</div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="card p-2">
                  <div className="text-xs font-semibold text-slate-500 mb-1 px-1">
                    Timeline (ms)
                  </div>
                  <ResponsiveContainer width="100%" height={120}>
                    <BarChart
                      data={selected.queries.map((q, i) => ({
                        idx: `#${i + 1}`,
                        ms: q.duration_ms,
                        op: q.operation,
                      }))}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="idx" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="ms">
                        {selected.queries.map((q, i) => (
                          <Cell
                            key={i}
                            fill={
                              q.operation === "SELECT"
                                ? "#3b82f6"
                                : q.operation === "INSERT"
                                  ? "#10b981"
                                  : q.operation === "UPDATE"
                                    ? "#f59e0b"
                                    : q.operation === "DELETE"
                                      ? "#ef4444"
                                      : "#64748b"
                            }
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <div className="space-y-2">
                  {selected.queries.map((q, i) => (
                    <div key={i} className="card p-2 text-xs">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className={`badge ${OP_COLOR[q.operation]}`}>{q.operation}</span>
                        <span className="text-slate-500">#{i + 1}</span>
                        <span className="text-slate-500">{q.duration_ms}ms</span>
                        {q.row_count !== null && (
                          <span className="text-slate-500">rows: {q.row_count}</span>
                        )}
                        {q.tables.map((t) => (
                          <span
                            key={t}
                            className="badge bg-slate-100 text-slate-600 font-mono"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                      <pre className="prism-okaidia-bg p-2 rounded overflow-x-auto">
                        <code className="language-sql">{q.sql}</code>
                      </pre>
                      {q.parameters && (
                        <div className="mt-1 text-[11px] text-slate-500 font-mono break-all">
                          params: {q.parameters}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="text-sm text-slate-500">No request selected.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
