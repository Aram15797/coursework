import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";

import { authApi } from "@/api/endpoints";
import { useAuthStore } from "@/store/auth-store";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { accessToken, user, setSession, clear } = useAuthStore();
  const [checking, setChecking] = useState(!accessToken);

  useEffect(() => {
    if (!accessToken) {
      authApi
        .refresh()
        .then((data) => setSession(data.access_token, data.user))
        .catch(() => clear())
        .finally(() => setChecking(false));
    }
  }, [accessToken, setSession, clear]);

  if (checking) {
    return (
      <div className="flex h-screen items-center justify-center text-slate-500">
        Loading session…
      </div>
    );
  }

  if (!accessToken || !user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
