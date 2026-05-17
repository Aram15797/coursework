import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, Shield, UserCheck, UserMinus, ShieldAlert, Check } from "lucide-react";
import { useState } from "react";

import { usersApi } from "@/api/endpoints";
import { useAuthStore } from "@/store/auth-store";
import { cn, initials, formatDate } from "@/lib/utils";
import type { User, UserRole } from "@/types";

const ROLE_COLORS: Record<UserRole, { badge: string; text: string; dot: string }> = {
  superadmin: {
    badge: "bg-indigo-50 border border-indigo-100 text-indigo-700",
    text: "text-indigo-800 font-semibold",
    dot: "bg-indigo-600",
  },
  admin: {
    badge: "bg-blue-50 border border-blue-100 text-blue-700",
    text: "text-blue-800 font-semibold",
    dot: "bg-blue-600",
  },
  manager: {
    badge: "bg-emerald-50 border border-emerald-100 text-emerald-700",
    text: "text-emerald-800 font-semibold",
    dot: "bg-emerald-600",
  },
  member: {
    badge: "bg-slate-50 border border-slate-200 text-slate-700",
    text: "text-slate-800",
    dot: "bg-slate-500",
  },
};

export function UserManagementPage() {
  const qc = useQueryClient();
  const currentUser = useAuthStore((s) => s.user);
  const [search, setSearch] = useState("");
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null);
  const [successUserId, setSuccessUserId] = useState<string | null>(null);

  const { data: users = [], isLoading, error } = useQuery({
    queryKey: ["users"],
    queryFn: () => usersApi.list(),
  });

  const updateMutation = useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: { role?: UserRole; is_active?: boolean } }) =>
      usersApi.adminUpdate(userId, data),
    onMutate: ({ userId }) => {
      setUpdatingUserId(userId);
    },
    onSuccess: (updatedUser) => {
      qc.invalidateQueries({ queryKey: ["users"] });
      // If the current user updated their own role (though not standard), update the auth store.
      if (updatedUser.id === currentUser?.id) {
        useAuthStore.getState().setUser(updatedUser);
      }
      setSuccessUserId(updatedUser.id);
      setTimeout(() => setSuccessUserId(null), 1500);
    },
    onError: (err: any) => {
      alert(err?.response?.data?.detail || "An error occurred while updating the user");
    },
    onSettled: () => {
      setUpdatingUserId(null);
    },
  });

  const filteredUsers = users.filter(
    (u) =>
      u.username.toLowerCase().includes(search.toLowerCase()) ||
      (u.full_name && u.full_name.toLowerCase().includes(search.toLowerCase())) ||
      u.email.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800 flex items-center gap-2">
            <Shield className="h-6 w-6 text-brand-600" />
            User Management
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            View all system users, assign access roles, and manage active accounts.
          </p>
        </div>
      </div>

      {/* Main Card */}
      <div className="card overflow-hidden">
        {/* Toolbar */}
        <div className="bg-slate-50 border-b border-slate-100 p-4 flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="relative w-full sm:max-w-md">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by name, username, or email..."
              className="input pl-9"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="text-xs text-slate-500 font-medium">
            Showing {filteredUsers.length} of {users.length} users
          </div>
        </div>

        {/* Table/Content State */}
        {isLoading ? (
          <div className="p-8 text-center text-slate-500">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-brand-200 border-t-brand-600 mb-2"></div>
            <div>Loading users list...</div>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500 flex flex-col items-center justify-center gap-2">
            <ShieldAlert className="h-10 w-10 text-red-500" />
            <div className="font-semibold">Failed to load users</div>
            <div className="text-xs text-slate-500">Make sure you have administrative privileges.</div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left">
              <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-3.5">User</th>
                  <th className="px-6 py-3.5">System Role</th>
                  <th className="px-6 py-3.5 text-center">Status</th>
                  <th className="px-6 py-3.5">Registered</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-100 text-sm">
                {filteredUsers.map((user) => {
                  const isSelf = user.id === currentUser?.id;
                  const isSuperAdmin = user.role === "superadmin";
                  const cannotModify = isSuperAdmin && currentUser?.role !== "superadmin";

                  return (
                    <tr
                      key={user.id}
                      className={cn(
                        "hover:bg-slate-50/50 transition-colors",
                        isSelf ? "bg-brand-50/10" : "",
                      )}
                    >
                      {/* Profile info */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 flex-shrink-0 flex items-center justify-center rounded-full bg-brand-100 text-brand-700 font-semibold text-sm shadow-inner">
                            {initials(user.full_name || user.username)}
                          </div>
                          <div>
                            <div className="font-medium text-slate-800 flex items-center gap-1.5">
                              {user.full_name || user.username}
                              {isSelf && (
                                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-brand-100 text-brand-800">
                                  You
                                </span>
                              )}
                            </div>
                            <div className="text-xs text-slate-400 font-mono">{user.email}</div>
                          </div>
                        </div>
                      </td>

                      {/* System Role Dropdown */}
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          {cannotModify ? (
                            <span className={cn("badge", ROLE_COLORS[user.role].badge)}>
                              {user.role}
                            </span>
                          ) : (
                            <div className="relative">
                              <select
                                value={user.role}
                                disabled={updatingUserId === user.id}
                                onChange={(e) =>
                                  updateMutation.mutate({
                                    userId: user.id,
                                    data: { role: e.target.value as UserRole },
                                  })
                                }
                                className={cn(
                                  "rounded px-2.5 py-1 text-xs font-medium border-0 cursor-pointer shadow-sm ring-1 ring-inset focus:ring-2 focus:ring-brand-600 transition-shadow",
                                  ROLE_COLORS[user.role].badge,
                                  updatingUserId === user.id ? "opacity-50 pointer-events-none" : "",
                                )}
                              >
                                <option value="member">member</option>
                                <option value="manager">manager</option>
                                <option value="admin">admin</option>
                                {currentUser?.role === "superadmin" && (
                                  <option value="superadmin">superadmin</option>
                                )}
                              </select>
                            </div>
                          )}

                          {/* Inline loaders / success notifications */}
                          {updatingUserId === user.id && (
                            <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600"></div>
                          )}
                          {successUserId === user.id && (
                            <Check className="h-4 w-4 text-emerald-600 animate-pulse" />
                          )}
                        </div>
                      </td>

                      {/* Account active switch */}
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <div className="flex items-center justify-center gap-2">
                          <button
                            type="button"
                            onClick={() =>
                              updateMutation.mutate({
                                userId: user.id,
                                data: { is_active: !user.is_active },
                              })
                            }
                            disabled={isSelf || cannotModify || updatingUserId === user.id}
                            className={cn(
                              "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2",
                              user.is_active ? "bg-brand-600" : "bg-slate-200",
                              (isSelf || cannotModify || updatingUserId === user.id)
                                ? "opacity-50 cursor-not-allowed"
                                : "",
                            )}
                          >
                            <span
                              className={cn(
                                "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out",
                                user.is_active ? "translate-x-5" : "translate-x-0",
                              )}
                            />
                          </button>
                          <span
                            className={cn(
                              "text-xs font-semibold w-12 text-left",
                              user.is_active ? "text-brand-700" : "text-slate-400",
                            )}
                          >
                            {user.is_active ? "Active" : "Inactive"}
                          </span>
                        </div>
                      </td>

                      {/* Date registered */}
                      <td className="px-6 py-4 whitespace-nowrap text-slate-500 font-mono text-xs">
                        {formatDate(user.created_at)}
                      </td>

                      {/* Quick diagnostic view */}
                      <td className="px-6 py-4 whitespace-nowrap text-right text-xs font-medium">
                        {user.is_active ? (
                          <span className="text-emerald-600 flex items-center justify-end gap-1 font-semibold">
                            <UserCheck className="h-3.5 w-3.5" />
                            Access Enabled
                          </span>
                        ) : (
                          <span className="text-slate-400 flex items-center justify-end gap-1">
                            <UserMinus className="h-3.5 w-3.5" />
                            Suspended
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}

                {!filteredUsers.length && (
                  <tr>
                    <td colSpan={5} className="px-6 py-10 text-center text-slate-500">
                      No users match your search query.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
