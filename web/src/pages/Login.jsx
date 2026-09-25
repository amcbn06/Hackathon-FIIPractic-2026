import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useToast, Spinner } from "../components/ui";

export default function Login() {
  const { login, signup } = useAuth();
  const toast = useToast();
  const [mode, setMode] = useState("login");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ email: "", password: "", displayName: "" });

  const upd = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "login") {
        await login(form.email, form.password);
      } else {
        await signup(form.email, form.password, form.displayName);
        toast.success("Welcome to South!");
      }
    } catch (err) {
      toast.error(err.message || "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  const useDemo = () => setForm({ email: "demo@onepick.app", password: "demo1234", displayName: "" });

  return (
    <div className="relative flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md animate-fade-up">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 grid h-16 w-16 place-items-center rounded-2xl bg-brand-600 text-3xl shadow-glow">
            📍
          </div>
          <h1 className="font-display text-4xl font-bold tracking-tight">South</h1>
          <p className="mt-2 text-slate-400">Stop choosing. Start going.</p>
          <p className="text-sm text-slate-500">One recommendation, not fifty.</p>
        </div>

        <div className="card p-6">
          <div className="mb-6 grid grid-cols-2 gap-1 rounded-xl bg-ink-800/80 p-1">
            {["login", "signup"].map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`rounded-lg py-2 text-sm font-semibold capitalize transition ${
                  mode === m ? "bg-brand-600 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {m === "login" ? "Log in" : "Sign up"}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-4">
            {mode === "signup" && (
              <div>
                <label className="label">Display name</label>
                <input
                  className="input mt-1"
                  placeholder="Alex"
                  value={form.displayName}
                  onChange={upd("displayName")}
                />
              </div>
            )}
            <div>
              <label className="label">Email</label>
              <input
                type="email"
                required
                className="input mt-1"
                placeholder="you@example.com"
                value={form.email}
                onChange={upd("email")}
              />
            </div>
            <div>
              <label className="label">Password</label>
              <input
                type="password"
                required
                className="input mt-1"
                placeholder="••••••••"
                value={form.password}
                onChange={upd("password")}
              />
            </div>
            <button type="submit" className="btn-primary w-full" disabled={busy}>
              {busy ? <Spinner /> : mode === "login" ? "Log in" : "Create account"}
            </button>
          </form>

          <button
            onClick={useDemo}
            className="mt-4 w-full text-center text-xs text-slate-500 hover:text-brand-300"
          >
            Use demo account · demo@onepick.app / demo1234
          </button>
        </div>
      </div>
    </div>
  );
}
