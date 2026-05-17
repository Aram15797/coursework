import { Database } from "lucide-react";

import { useInspectorStore } from "@/store/inspector-store";
import { cn } from "@/lib/utils";

export function InspectorToggle() {
  const { enabled, open, toggleEnabled, setOpen, logs } = useInspectorStore();
  const last = logs[0];
  return (
    <div className="flex items-center gap-2">
      {enabled && last && (
        <button
          onClick={() => setOpen(!open)}
          className="text-xs px-2 py-1 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700"
        >
          {last.query_count} queries · {last.total_duration_ms}ms
        </button>
      )}
      <button
        onClick={toggleEnabled}
        className={cn(
          "btn",
          enabled
            ? "bg-emerald-100 text-emerald-700 hover:bg-emerald-200"
            : "bg-slate-100 text-slate-700 hover:bg-slate-200",
        )}
        title="Toggle DB Inspector"
      >
        <Database className="h-4 w-4" />
        DB Inspector {enabled ? "ON" : "OFF"}
      </button>
    </div>
  );
}
