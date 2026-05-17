import axios from "axios";

import { useAuthStore } from "@/store/auth-store";
import { useInspectorStore } from "@/store/inspector-store";
import type { QueryLog } from "@/types";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

function decodeQueryLogHeader(value: string | null): QueryLog | null {
  if (!value) return null;
  try {
    const decoded = atob(value);
    return JSON.parse(decoded) as QueryLog;
  } catch {
    return null;
  }
}

api.interceptors.response.use(
  (response) => {
    const header = response.headers?.["x-db-query-log"];
    const log = decodeQueryLogHeader(header || null);
    if (log) {
      useInspectorStore.getState().pushLog(log);
    }
    return response;
  },
  async (error) => {
    if (error.response?.status === 401 && !error.config?._retried) {
      error.config._retried = true;
      try {
        const refreshResp = await axios.post(
          (import.meta.env.VITE_API_BASE_URL || "/api") + "/auth/refresh",
          {},
          { withCredentials: true },
        );
        const { access_token, user } = refreshResp.data;
        useAuthStore.getState().setSession(access_token, user);
        error.config.headers.Authorization = `Bearer ${access_token}`;
        return api.request(error.config);
      } catch {
        useAuthStore.getState().clear();
      }
    }
    return Promise.reject(error);
  },
);
