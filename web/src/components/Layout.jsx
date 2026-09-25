import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV = [
  { to: "/", label: "Discover", icon: "🎯", end: true },
  { to: "/itinerary", label: "Itinerary", icon: "🗺️" },
  { to: "/friends", label: "Friends", icon: "👥" },
  { to: "/streak", label: "Streak", icon: "🔥" },
  { to: "/history", label: "Tracker", icon: "📜" },
  { to: "/spots", label: "Spots", icon: "✨" },
];

function Brand() {
  return (
    <div className="flex items-center gap-2">
      <div className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-lg shadow-glow">
        📍
      </div>
      <div className="leading-tight">
        <div className="font-display text-lg font-bold tracking-tight">South</div>
        <div className="text-[10px] uppercase tracking-widest text-slate-500">
          one pick, not fifty
        </div>
      </div>
    </div>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const doLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-6xl gap-0 md:gap-6 md:px-6">
      {/* Sidebar (desktop) */}
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col py-6 md:flex">
        <div className="px-2">
          <Brand />
        </div>
        <nav className="mt-8 flex flex-1 flex-col gap-1">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? "bg-brand-600/20 text-white ring-1 ring-brand-500/40"
                    : "text-slate-400 hover:bg-white/5 hover:text-slate-100"
                }`
              }
            >
              <span className="text-base">{n.icon}</span>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="card mt-4 p-3">
          <div className="truncate text-sm font-semibold">
            {user?.display_name}
          </div>
          <div className="truncate text-xs text-slate-500">{user?.email}</div>
          {user?.invite_code && (
            <div className="mt-2 flex items-center justify-between rounded-lg bg-white/5 px-2 py-1.5">
              <span className="text-[10px] uppercase tracking-wide text-slate-500">
                Invite
              </span>
              <code className="text-xs font-bold text-brand-300">
                {user.invite_code}
              </code>
            </div>
          )}
          <button onClick={doLogout} className="btn-ghost mt-3 w-full text-xs">
            Log out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="w-full flex-1 px-4 pb-28 pt-6 md:px-0 md:pb-10">
        <div className="mb-5 flex items-center justify-between md:hidden">
          <Brand />
          <button onClick={doLogout} className="btn-ghost text-xs">
            Log out
          </button>
        </div>
        <Outlet />
      </main>

      {/* Bottom nav (mobile) */}
      <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-white/10 bg-ink-950/90 backdrop-blur-xl md:hidden">
        <div className="mx-auto flex max-w-md items-center justify-between px-2">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[10px] font-medium transition ${
                  isActive ? "text-brand-300" : "text-slate-500"
                }`
              }
            >
              <span className="text-lg">{n.icon}</span>
              {n.label}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}
