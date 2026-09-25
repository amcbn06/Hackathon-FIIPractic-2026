import { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { FullPageSpinner, EmptyState, useToast } from "../components/ui";
import { catIcon } from "../lib/constants";

function Section({ title, children }) {
  return (
    <div className="space-y-2">
      <div className="label">{title}</div>
      {children}
    </div>
  );
}

function PickRow({ item }) {
  return (
    <div className="card flex items-center justify-between p-4">
      <div>
        <div className="font-semibold">
          {catIcon(item.category)} {item.place_name}
        </div>
        <div className="text-xs text-slate-400">{item.city}</div>
      </div>
    </div>
  );
}

function GroupRow({ item }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <div className="font-semibold">
          {catIcon(item.category)} {item.place_name}
        </div>
        <span className="chip">{item.group_name}</span>
      </div>
      <div className="mt-2 flex items-center gap-2 text-xs text-slate-400">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full bg-brand-500"
            style={{ width: `${(item.checked_in_count / item.total_members) * 100}%` }}
          />
        </div>
        {item.checked_in_count}/{item.total_members} checked in
        {item.i_checked_in && <span className="text-emerald-400">· you ✓</span>}
      </div>
    </div>
  );
}

function ItineraryRow({ item, onTick }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <div className="font-semibold">🗺️ {item.city}</div>
        <span className="text-xs text-slate-400">
          {item.visited_stops}/{item.total_stops} · {item.created_at}
        </span>
      </div>
      <div className="mt-3 space-y-1.5">
        {item.stops.map((s) => (
          <button
            key={s.stop_id}
            disabled={s.visited}
            onClick={() => onTick(s.stop_id)}
            className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition ${
              s.visited
                ? "bg-emerald-600/15 text-emerald-300"
                : "bg-white/5 hover:bg-white/10"
            }`}
          >
            <span>{s.visited ? "✓" : catIcon(s.category)}</span>
            <span className={s.visited ? "line-through opacity-70" : ""}>
              {s.place_name}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function Tracker() {
  const toast = useToast();
  const [data, setData] = useState(null);
  const [tab, setTab] = useState("todo");
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    api.tracker().then(setData).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const tickStop = async (stopId) => {
    try {
      await api.markStop(stopId);
      toast.success("Stop checked off");
      load();
    } catch (err) {
      toast.error(err.message);
    }
  };

  if (loading) return <FullPageSpinner />;

  const bucket = data[tab];
  const empty =
    !bucket.solo.length && !bucket.group.length && !bucket.itineraries.length;

  return (
    <div className="animate-fade-up space-y-6">
      <header>
        <h1 className="font-display text-3xl font-bold tracking-tight">Tracker</h1>
        <p className="mt-1 text-slate-400">
          What's still on your list and where you've been.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-1 rounded-xl bg-ink-800/80 p-1">
        {[
          ["todo", "To-do"],
          ["history", "Visited"],
        ].map(([k, label]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`rounded-lg py-2 text-sm font-semibold transition ${
              tab === k ? "bg-brand-600 text-white" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {empty ? (
        <EmptyState
          icon={tab === "todo" ? "📝" : "🏁"}
          title={tab === "todo" ? "Nothing pending" : "No visits yet"}
          subtitle={
            tab === "todo"
              ? "Make a pick and it'll show up here until you visit it."
              : "Once you mark picks as visited they'll appear here."
          }
        />
      ) : (
        <div className="space-y-6">
          {bucket.solo.length > 0 && (
            <Section title="Solo picks">
              <div className="space-y-2">
                {bucket.solo.map((i) => <PickRow key={i.pick_id} item={i} />)}
              </div>
            </Section>
          )}
          {bucket.group.length > 0 && (
            <Section title="Group picks">
              <div className="space-y-2">
                {bucket.group.map((i) => <GroupRow key={i.pick_id} item={i} />)}
              </div>
            </Section>
          )}
          {bucket.itineraries.length > 0 && (
            <Section title="Itineraries">
              <div className="space-y-2">
                {bucket.itineraries.map((i) => (
                  <ItineraryRow key={i.itinerary_id} item={i} onTick={tickStop} />
                ))}
              </div>
            </Section>
          )}
        </div>
      )}
    </div>
  );
}
