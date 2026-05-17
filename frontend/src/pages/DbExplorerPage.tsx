import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  Edge,
  MarkerType,
  MiniMap,
  Node,
  NodeProps,
  Position,
  Handle,
} from "reactflow";
import "reactflow/dist/style.css";

import { dbApi } from "@/api/endpoints";
import type { DbSchemaTable } from "@/types";

function TableNode({ data }: NodeProps<DbSchemaTable & { onSelect: () => void }>) {
  return (
    <div
      className="bg-white border-2 border-brand-400 rounded-md min-w-[220px] shadow-sm cursor-pointer"
      onClick={data.onSelect}
    >
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
      <div className="bg-brand-600 text-white text-sm font-semibold px-3 py-1.5 rounded-t-sm">
        {data.name}
      </div>
      <div className="text-xs">
        {data.columns.slice(0, 8).map((c) => {
          const isPk = data.primary_key.includes(c.name);
          const isFk = data.foreign_keys.some((fk) => fk.column === c.name);
          return (
            <div
              key={c.name}
              className="px-3 py-1 border-t border-slate-100 flex justify-between gap-2"
            >
              <span className="font-mono">
                {isPk && <span className="text-amber-600">🔑</span>}
                {isFk && <span className="text-blue-600">🔗</span>} {c.name}
              </span>
              <span className="text-slate-400">{c.type}</span>
            </div>
          );
        })}
        {data.columns.length > 8 && (
          <div className="px-3 py-1 text-slate-400 border-t border-slate-100">
            +{data.columns.length - 8} more…
          </div>
        )}
      </div>
    </div>
  );
}

const nodeTypes = { table: TableNode };

export function DbExplorerPage() {
  const schema = useQuery({ queryKey: ["db-schema"], queryFn: dbApi.schema });
  const indexes = useQuery({ queryKey: ["db-indexes"], queryFn: dbApi.indexes });
  const stats = useQuery({ queryKey: ["db-stats"], queryFn: dbApi.stats });
  const [selected, setSelected] = useState<string | null>(null);

  const { nodes, edges } = useMemo(() => {
    const tables = schema.data?.tables || [];
    const cols = 3;
    const ns: Node[] = tables.map((t, i) => ({
      id: t.name,
      type: "table",
      position: { x: (i % cols) * 320, y: Math.floor(i / cols) * 280 },
      data: { ...t, onSelect: () => setSelected(t.name) },
    }));
    const es: Edge[] = [];
    tables.forEach((t) =>
      t.foreign_keys.forEach((fk, idx) => {
        es.push({
          id: `${t.name}-${fk.name}-${idx}`,
          source: t.name,
          target: fk.references_table,
          label: `${fk.column} → ${fk.references_column}`,
          markerEnd: { type: MarkerType.ArrowClosed },
          style: { stroke: "#6366f1" },
          labelStyle: { fontSize: 10 },
        });
      }),
    );
    return { nodes: ns, edges: es };
  }, [schema.data]);

  useEffect(() => {
    if (!selected && schema.data?.tables.length) {
      setSelected(schema.data.tables[0].name);
    }
  }, [schema.data, selected]);

  const selectedTable = schema.data?.tables.find((t) => t.name === selected);
  const tableIndexes = indexes.data?.indexes.filter((i) => i.table === selected) || [];
  const tableStats = stats.data?.tables.find((s) => s.table_name === selected);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Database Schema Explorer</h1>
      <div className="grid grid-cols-12 gap-4 h-[calc(100vh-220px)]">
        <div className="col-span-8 card overflow-hidden">
          {schema.isLoading ? (
            <div className="p-4 text-slate-500">Loading schema…</div>
          ) : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              fitView
              minZoom={0.2}
            >
              <Background />
              <MiniMap pannable zoomable />
              <Controls />
            </ReactFlow>
          )}
        </div>
        <div className="col-span-4 card p-4 overflow-y-auto">
          {selectedTable ? (
            <div className="space-y-4 text-sm">
              <h2 className="font-bold text-lg">{selectedTable.name}</h2>
              {tableStats && (
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-slate-50 p-2 rounded">
                    <div className="text-slate-500">Rows</div>
                    <div className="font-bold">{tableStats.row_count}</div>
                  </div>
                  <div className="bg-slate-50 p-2 rounded">
                    <div className="text-slate-500">Size</div>
                    <div className="font-bold">{tableStats.total_size}</div>
                  </div>
                  <div className="bg-slate-50 p-2 rounded">
                    <div className="text-slate-500">Seq scans</div>
                    <div className="font-bold">{tableStats.seq_scan}</div>
                  </div>
                  <div className="bg-slate-50 p-2 rounded">
                    <div className="text-slate-500">Index scans</div>
                    <div className="font-bold">{tableStats.idx_scan}</div>
                  </div>
                </div>
              )}
              <div>
                <h3 className="font-semibold mb-1">Columns</h3>
                <table className="w-full text-xs">
                  <thead className="text-slate-500">
                    <tr>
                      <th className="text-left">Name</th>
                      <th className="text-left">Type</th>
                      <th className="text-left">Null</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedTable.columns.map((c) => (
                      <tr key={c.name} className="border-t border-slate-100">
                        <td className="font-mono py-1">{c.name}</td>
                        <td>{c.type}</td>
                        <td>{c.nullable ? "yes" : "no"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div>
                <h3 className="font-semibold mb-1">Primary Key</h3>
                <div className="text-xs font-mono">
                  {selectedTable.primary_key.join(", ") || "—"}
                </div>
              </div>
              <div>
                <h3 className="font-semibold mb-1">Foreign Keys</h3>
                {selectedTable.foreign_keys.length ? (
                  <ul className="text-xs space-y-1">
                    {selectedTable.foreign_keys.map((fk) => (
                      <li key={fk.name} className="font-mono">
                        {fk.column} → {fk.references_table}.{fk.references_column}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-xs text-slate-500">None</div>
                )}
              </div>
              <div>
                <h3 className="font-semibold mb-1">Indexes ({tableIndexes.length})</h3>
                <ul className="text-xs space-y-1">
                  {tableIndexes.map((i) => (
                    <li key={i.name} className="font-mono break-all">
                      <div className="font-bold">{i.name}</div>
                      <div className="text-slate-500">{i.definition}</div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <div className="text-sm text-slate-500">Select a table to inspect.</div>
          )}
        </div>
      </div>
    </div>
  );
}
