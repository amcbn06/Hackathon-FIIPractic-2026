import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { FullPageSpinner, useToast, Spinner, EmptyState, Stars } from "../components/ui";
import { CATEGORIES, catIcon } from "../lib/constants";

export default function Spots() {
  const { user } = useAuth();
  const toast = useToast();
  const [tab, setTab] = useState("mine");
  const [loading, setLoading] = useState(true);

  const [mine, setMine] = useState([]);
  const [pending, setPending] = useState([]);

  const load = useCallback(async () => {
    try {
      const [m, p] = await Promise.all([
        api.customLocations(),
        api.pendingPlaces(),
      ]);
      setMine(m);
      setPending(p);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <FullPageSpinner />;

  return (
    <div className="animate-fade-up space-y-6">
      <header>
        <h1 className="font-display text-3xl font-bold tracking-tight">Spots</h1>
        <p className="mt-1 text-slate-400">
          Your private finds and community places waiting for votes.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-1 rounded-xl bg-ink-800/80 p-1">
        {[
          ["mine", "My secret spots"],
          ["community", "Vote community"],
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

      {tab === "mine" ? (
        <MySpots mine={mine} reload={load} toast={toast} />
      ) : (
        <Community pending={pending} reload={load} toast={toast} isAdmin={user?.is_admin} />
      )}
    </div>
  );
}

function MySpots({ mine, reload, toast }) {
  const [form, setForm] = useState({ name: "", city: "Iași", rating: 5, description: "" });
  const [busy, setBusy] = useState(false);

  const add = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await api.addCustomLocation(form);
      toast.success(res.ai_generated ? "Validated & auto-described by AI ✨" : "Saved");
      setForm({ name: "", city: form.city, rating: 5, description: "" });
      reload();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <form onSubmit={add} className="card space-y-3 p-5">
        <div className="label">Add a secret spot</div>
        <input
          className="input"
          placeholder="Place name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
        />
        <div className="grid grid-cols-2 gap-3">
          <input
            className="input"
            placeholder="City"
            value={form.city}
            onChange={(e) => setForm({ ...form, city: e.target.value })}
          />
          <select
            className="input"
            value={form.rating}
            onChange={(e) => setForm({ ...form, rating: Number(e.target.value) })}
          >
            {[5, 4, 3, 2, 1].map((n) => (
              <option key={n} value={n}>{"★".repeat(n)}</option>
            ))}
          </select>
        </div>
        <textarea
          className="input min-h-[70px]"
          placeholder="Your notes (leave empty — AI writes one for you)"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
        <button className="btn-primary w-full" disabled={busy}>
          {busy ? <Spinner /> : "✨ Validate & save"}
        </button>
      </form>

      {mine.length === 0 ? (
        <EmptyState icon="✨" title="No secret spots yet" subtitle="Add your favorite hidden gems above." />
      ) : (
        mine.map((s) => (
          <div key={s.id} className="card p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 font-semibold">
                  {s.name}
                  {s.ai_generated && <span className="chip">AI</span>}
                </div>
                <Stars value={s.rating} />
                <p className="mt-1 text-sm text-slate-400">{s.description}</p>
                {s.interval && <p className="mt-1 text-xs text-slate-500">🕒 {s.interval}</p>}
              </div>
              <button
                onClick={async () => {
                  await api.deleteCustomLocation(s.id);
                  toast.info("Deleted");
                  reload();
                }}
                className="text-slate-500 hover:text-rose-400"
              >
                ✕
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

function Community({ pending, reload, toast, isAdmin }) {
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    name: "", address: "", city: "Iași", category: "cafe",
    lat: 47.16, lon: 27.58, description: "",
  });

  const suggest = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.suggestPlace({
        ...form,
        lat: Number(form.lat),
        lon: Number(form.lon),
      });
      toast.success("Suggested! Now it needs community votes.");
      setShowForm(false);
      setForm({ ...form, name: "", address: "", description: "" });
      reload();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  };

  const act = (fn, msg) => async () => {
    try {
      await fn();
      toast.success(msg);
      reload();
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <div className="space-y-4">
      <button onClick={() => setShowForm((s) => !s)} className="btn-ghost w-full">
        {showForm ? "Cancel" : "+ Suggest a new place"}
      </button>

      {showForm && (
        <form onSubmit={suggest} className="card space-y-3 p-5 animate-fade-up">
          <input className="input" placeholder="Name" value={form.name} required
            onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input className="input" placeholder="Address" value={form.address}
            onChange={(e) => setForm({ ...form, address: e.target.value })} />
          <div className="grid grid-cols-2 gap-3">
            <input className="input" placeholder="City" value={form.city}
              onChange={(e) => setForm({ ...form, city: e.target.value })} />
            <select className="input" value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}>
              {CATEGORIES.map((c) => (
                <option key={c.key} value={c.key}>{c.label}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <input className="input" type="number" step="any" placeholder="Latitude" value={form.lat}
              onChange={(e) => setForm({ ...form, lat: e.target.value })} />
            <input className="input" type="number" step="any" placeholder="Longitude" value={form.lon}
              onChange={(e) => setForm({ ...form, lon: e.target.value })} />
          </div>
          <textarea className="input min-h-[60px]" placeholder="Why it's good" value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <button className="btn-primary w-full" disabled={busy}>
            {busy ? <Spinner /> : "Submit for votes"}
          </button>
        </form>
      )}

      {pending.length === 0 ? (
        <EmptyState icon="🗳️" title="Nothing pending" subtitle="No community places are waiting for votes right now." />
      ) : (
        pending.map((p) => (
          <div key={p.id} className="card flex items-center justify-between p-4">
            <div>
              <div className="font-semibold">{catIcon(p.category)} {p.name}</div>
              <div className="text-xs text-slate-400">{p.address || p.city}</div>
              <div className="mt-1 text-xs text-brand-300">{p.vote_count} votes</div>
            </div>
            <div className="flex gap-2">
              <button onClick={act(() => api.votePlace(p.id), "Voted")} className="btn-primary text-xs">
                ⬆ Vote
              </button>
              {isAdmin && (
                <>
                  <button onClick={act(() => api.approvePlace(p.id), "Approved")} className="btn-ghost text-xs">
                    Approve
                  </button>
                  <button onClick={act(() => api.rejectPlace(p.id), "Rejected")} className="btn-danger text-xs">
                    Reject
                  </button>
                </>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
