import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { FullPageSpinner } from "../components/ui";

export default function Streak() {
  const [streak, setStreak] = useState(null);
  const [calendar, setCalendar] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.streak(), api.streakCalendar(35)])
      .then(([s, c]) => {
        setStreak(s);
        setCalendar(c.slice().reverse()); // oldest -> newest
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <FullPageSpinner />;

  return (
    <div className="animate-fade-up space-y-6">
      <header>
        <h1 className="font-display text-3xl font-bold tracking-tight">Streak</h1>
        <p className="mt-1 text-slate-400">Visit a pick each day to keep it alive.</p>
      </header>

      <div className="grid grid-cols-2 gap-4">
        <div className="card flex flex-col items-center gap-1 p-6 text-center">
          <div className="text-5xl">🔥</div>
          <div className="font-display text-4xl font-bold text-accent-400">
            {streak.current}
          </div>
          <div className="label">Current streak</div>
        </div>
        <div className="card flex flex-col items-center gap-1 p-6 text-center">
          <div className="text-5xl">🏆</div>
          <div className="font-display text-4xl font-bold text-brand-300">
            {streak.longest}
          </div>
          <div className="label">Longest ever</div>
        </div>
      </div>

      <div className="card p-5">
        <div className="label mb-3">Last 35 days</div>
        <div className="grid grid-cols-7 gap-1.5">
          {calendar.map((d) => (
            <div
              key={d.date}
              title={`${d.date}${d.visited ? " · visited" : ""}`}
              className={`aspect-square rounded-md transition ${
                d.visited
                  ? "bg-accent-500 shadow-[0_0_10px_-2px_rgba(249,115,22,0.6)]"
                  : "bg-white/5"
              }`}
            />
          ))}
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Last visit: {streak.last_visit_date || "—"}
        </p>
      </div>
    </div>
  );
}
