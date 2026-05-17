import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { authApi } from "@/api/endpoints";
import { useAuthStore } from "@/store/auth-store";

export function RegisterPage() {
  const navigate = useNavigate();
  const setSession = useAuthStore((s) => s.setSession);
  const [form, setForm] = useState({
    email: "",
    username: "",
    full_name: "",
    password: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await authApi.register(form);
      const data = await authApi.login(form.email, form.password);
      setSession(data.access_token, data.user);
      navigate("/dashboard");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-6">
      <form onSubmit={onSubmit} className="card w-full max-w-sm p-6 space-y-4">
        <h1 className="text-xl font-semibold text-center">Create account</h1>
        {(["email", "username", "full_name", "password"] as const).map((field) => (
          <div key={field}>
            <label className="label capitalize">{field.replace("_", " ")}</label>
            <input
              className="input"
              type={field === "password" ? "password" : field === "email" ? "email" : "text"}
              value={form[field]}
              onChange={(e) => setForm({ ...form, [field]: e.target.value })}
              required={field !== "full_name"}
            />
          </div>
        ))}
        {error && (
          <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}
        <button type="submit" className="btn-primary w-full" disabled={loading}>
          {loading ? "Creating…" : "Create account"}
        </button>
        <div className="text-center text-sm text-slate-500">
          Have an account?{" "}
          <Link to="/login" className="text-brand-600 hover:underline">
            Sign in
          </Link>
        </div>
      </form>
    </div>
  );
}
