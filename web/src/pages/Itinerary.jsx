import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useToast, Spinner, EmptyState } from "../components/ui";
import { CATEGORIES, catIcon, catLabel, directionsUrl } from "../lib/constants";

export default function Itinerary() {
  const toast = useToast();
  const [cities, setCities] = useState(["Iași"]);
  const [city, setCity] = useState("Iași");
  const [selected, setSelected] = useState(["cafe", "park", "viewpoint"]);
  const [route, setRoute] = useState(null);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.cities().then((c) => {
      setCities(c);
      setCity((p) => (c.includes(p) ? p : c[0]));
    }).catch(() => {});
  }, []);

  const toggle = (key) =>
    setSelected((s) =>
      s.includes(key) ? s.filter((x) => x !== key) : [...s, key]
    );

  const generate = async () => {
    if (!selected.length) return toast.error("Pick at least one vibe");
    setBusy(true);
    setRoute(null);
    try {
      const res = await api.itinerary(selected, city);
      setRoute(res);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    if (!route) return;
    setSaving(true);
    try {
      await api.saveItinerary(city, route.stops);
      toast.success("Saved to your tracker");
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="animate-fade-up space-y-6">
      <header>
        <h1 className="font-display text-3xl font-bold tracking-tight">Itinerary</h1>
        <p className="mt-1 text-slate-400">
          Chain a few vibes into one optimized route.
        </p>
      </header>

      <div className="card space-y-4 p-5">
        <div>
          <label className="label">City</label>
          <select className="input mt-1" value={city} onChange={(e) => setCity(e.target.value)}>
            {cities.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div>
          <div className="label mb-2">Vibes to include</div>
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map((c) => {
              const on = selected.includes(c.key);
              return (
                <button
                  key={c.key}
                  onClick={() => toggle(c.key)}
                  className={`rounded-full border px-3 py-1.5 text-sm font-medium transition ${
                    on
                      ? "border-brand-500/60 bg-brand-600/25 text-white"
                      : "border-white/10 bg-white/5 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {c.icon} {c.label}
                </button>
              );
            })}
          </div>
        </div>
        <button onClick={generate} disabled={busy} className="btn-primary w-full">
          {busy ? <Spinner /> : "Build my route"}
        </button>
      </div>

      {route && (
        <div className="animate-fade-up space-y-4">
          <div className="card flex items-center justify-between p-4">
            <div>
              <div className="text-sm font-semibold">{route.stops.length} stops</div>
              <div className="text-xs text-slate-400">~{route.total_minutes} min total</div>
            </div>
            <button onClick={save} disabled={saving} className="btn-ghost text-sm">
              {saving ? <Spinner /> : "💾 Save"}
            </button>
          </div>

          {route.insight && (
            <p className="rounded-xl border border-brand-500/20 bg-brand-600/10 p-4 text-sm text-brand-100">
              ✨ {route.insight}
            </p>
          )}

          <ol className="relative space-y-3 pl-6">
            <span className="absolute left-[9px] top-2 bottom-2 w-px bg-white/10" />
            {route.stops.map((s, i) => (
              <li key={s.place_id + i} className="relative">
                <span className="absolute -left-6 top-3 grid h-5 w-5 place-items-center rounded-full bg-brand-600 text-[10px] font-bold text-white">
                  {i + 1}
                </span>
                <div className="card flex items-center justify-between p-4">
                  <div>
                    <div className="font-semibold">
                      {catIcon(s.category)} {s.name}
                    </div>
                    <div className="text-xs text-slate-400">
                      {catLabel(s.category)}
                      {s.address ? ` · ${s.address}` : ""}
                    </div>
                  </div>
                  <a
                    href={directionsUrl(s.lat, s.lon)}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-ghost text-xs"
                  >
                    🧭
                  </a>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}

      {!route && !busy && (
        <EmptyState
          icon="🗺️"
          title="No route yet"
          subtitle="Choose your vibes above and build a route through the city."
        />
      )}
    </div>
  );
}
