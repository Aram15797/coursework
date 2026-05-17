import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { QueryLog } from "@/types";

interface InspectorState {
  enabled: boolean;
  open: boolean;
  logs: QueryLog[];
  selectedRequestId: string | null;
  toggleEnabled: () => void;
  setOpen: (open: boolean) => void;
  pushLog: (log: QueryLog) => void;
  selectRequest: (requestId: string | null) => void;
  clear: () => void;
}

const MAX_LOGS = 100;

export const useInspectorStore = create<InspectorState>()(
  persist(
    (set, get) => ({
      enabled: false,
      open: false,
      logs: [],
      selectedRequestId: null,
      toggleEnabled: () => {
        const next = !get().enabled;
        set({ enabled: next, open: next ? get().open : false });
      },
      setOpen: (open) => set({ open }),
      pushLog: (log) => {
        const logs = [log, ...get().logs].slice(0, MAX_LOGS);
        set({ logs, selectedRequestId: log.request_id });
      },
      selectRequest: (requestId) => set({ selectedRequestId: requestId }),
      clear: () => set({ logs: [], selectedRequestId: null }),
    }),
    {
      name: "ptms-inspector",
      partialize: (state) => ({ enabled: state.enabled }),
    },
  ),
);
