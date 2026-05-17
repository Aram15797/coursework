import { Database, LayoutDashboard, LogOut, FolderKanban } from "lucide-react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";

import { authApi } from "@/api/endpoints";
import { InspectorPanel } from "@/components/db-inspector/InspectorPanel";
import { InspectorToggle } from "@/components/db-inspector/InspectorToggle";
import { useAuthStore } from "@/store/auth-store";
import { cn, initials } from "@/lib/utils";

export function AppLayout() {
  const user = useAuthStore((s) => s.user);
  const clear = useAuthStore((s) => s.clear);
  const navigate = useNavigate();
  const isAdmin = user?.role === "superadmin" || user?.role === "admin";

  const logout = async () => {
    try {
      await authApi.logout();
    } catch {
      /* ignore */
    }
    clear();
    navigate("/login");
  };

  const navItem = (to: string, label: string, Icon: typeof LayoutDashboard) => (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium",
          isActive
            ? "bg-brand-50 text-brand-700"
            : "text-slate-600 hover:bg-slate-100",
        )
      }
    >
      <Icon className="h-4 w-4" />
      {label}
    </NavLink>
  );

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="hidden md:flex w-60 flex-col border-r border-slate-200 bg-white px-4 py-5">
        <Link to="/" className="mb-6 flex items-center gap-2 px-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white font-bold">
            P
          </div>
          <span className="font-semibold text-slate-800">PTMS</span>
        </Link>
        <nav className="flex-1 flex flex-col gap-1">
          {navItem("/dashboard", "Dashboard", LayoutDashboard)}
          {navItem("/projects", "Projects", FolderKanban)}
          {isAdmin && navItem("/db-explorer", "DB Explorer", Database)}
        </nav>
        <div className="mt-auto pt-4 border-t border-slate-100">
          <div className="flex items-center gap-2 px-2 py-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-brand-700 text-xs font-semibold">
              {initials(user?.full_name || user?.username)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">
                {user?.full_name || user?.username}
              </div>
              <div className="text-xs text-slate-500 truncate">{user?.role}</div>
            </div>
            <button onClick={logout} className="btn-ghost p-1.5" title="Logout">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
          <div className="font-semibold text-slate-700">
            Project &amp; Task Management
          </div>
          <InspectorToggle />
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
        <InspectorPanel />
      </div>
    </div>
  );
}
