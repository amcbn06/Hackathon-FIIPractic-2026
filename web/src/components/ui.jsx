import { createContext, useCallback, useContext, useState } from "react";

// --- Loading spinner ------------------------------------------------------

export function Spinner({ className = "" }) {
  return (
    <span
      className={`inline-block h-5 w-5 animate-spin rounded-full border-2 border-white/25 border-t-white ${className}`}
    />
  );
}

export function FullPageSpinner({ label = "Loading…" }) {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3 text-slate-400">
      <Spinner className="h-7 w-7" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

// --- Empty / error states -------------------------------------------------

export function EmptyState({ icon = "✨", title, subtitle, action }) {
  return (
    <div className="card flex flex-col items-center gap-2 px-6 py-12 text-center">
      <div className="text-4xl">{icon}</div>
      <h3 className="text-lg font-semibold">{title}</h3>
      {subtitle && <p className="max-w-sm text-sm text-slate-400">{subtitle}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function Stars({ value = 0 }) {
  const full = Math.max(0, Math.min(5, Math.round(value)));
  return (
    <span className="text-amber-400" title={`${value}`}>
      {"★".repeat(full)}
      <span className="text-slate-600">{"★".repeat(5 - full)}</span>
    </span>
  );
}

// --- Toasts ---------------------------------------------------------------

const ToastCtx = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const push = useCallback((message, type = "info") => {
    const id = Math.random().toString(36).slice(2);
    setToasts((t) => [...t, { id, message, type }]);
    setTimeout(() => {
      setToasts((t) => t.filter((x) => x.id !== id));
    }, 3200);
  }, []);

  const toast = {
    info: (m) => push(m, "info"),
    success: (m) => push(m, "success"),
    error: (m) => push(m, "error"),
  };

  return (
    <ToastCtx.Provider value={toast}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-6 z-50 flex flex-col items-center gap-2 px-4">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto animate-pop-in rounded-xl border px-4 py-3 text-sm font-medium shadow-card backdrop-blur-xl ${
              t.type === "error"
                ? "border-rose-500/30 bg-rose-950/80 text-rose-100"
                : t.type === "success"
                ? "border-emerald-500/30 bg-emerald-950/80 text-emerald-100"
                : "border-white/10 bg-ink-800/90 text-slate-100"
            }`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
