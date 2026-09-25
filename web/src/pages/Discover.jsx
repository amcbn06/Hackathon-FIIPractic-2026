import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { useToast, Spinner } from "../components/ui";
import { CATEGORIES } from "../lib/constants";

export default function Discover() {
  const { user } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();

  const [cities, setCities] = useState(["Iași"]);
  const [city, setCity] = useState("Iași");
  const [groups, setGroups] = useState([]);
  const [groupId, setGroupId] = useState("");
  const [pending, setPending] = useState(null); // category being fetched

  useEffect(() => {
    api.cities().then((c) => {
      setCities(c);
      setCity((prev) => (c.includes(prev) ? prev : c[0]));
    }).catch(() => {});
    api.groups().then(setGroups).catch(() => {});
  }, []);

  const doPick = async (cat) => {
    setPending(cat);
    try {
      const result = groupId
        ? await api.groupPick(Number(groupId), cat, city)
        : await api.pick(cat, city);
      navigate("/result", { state: { pick: result, group: !!groupId } });
    } catch (err) {
      toast.error(err.message || "No place found for that vibe");
    } finally {
      setPending(null);
    }
  };

  const firstName = (user?.display_name || "there").split(" ")[0];

  return (
    <div className="animate-fade-up space-y-6">
      <header>
        <h1 className="font-display text-3xl font-bold tracking-tight">
          Hey, {firstName} 👋
        </h1>
        <p className="mt-1 text-slate-400">Pick a vibe — we pick the place.</p>
      </header>

      <div className="card grid gap-4 p-5 sm:grid-cols-2">
        <div>
          <label className="label">Where are you?</label>
          <select
            className="input mt-1"
            value={city}
            onChange={(e) => setCity(e.target.value)}
          >
            {cities.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Deciding for…</label>
          <select
            className="input mt-1"
            value={groupId}
            onChange={(e) => setGroupId(e.target.value)}
          >
            <option value="">Just me</option>
            {groups.map((g) => (
              <option key={g.group_id} value={g.group_id}>
                {g.name} ({g.member_ids.length})
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <div className="label mb-3">What are you in the mood for?</div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {CATEGORIES.map((c) => {
            const busy = pending === c.key;
            return (
              <button
                key={c.key}
                disabled={!!pending}
                onClick={() => doPick(c.key)}
                className={`group relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br ${c.tint} p-5 text-left transition hover:border-brand-500/50 hover:shadow-glow disabled:opacity-60`}
              >
                <div className="text-3xl transition group-hover:scale-110">
                  {busy ? <Spinner className="h-7 w-7" /> : c.icon}
                </div>
                <div className="mt-3 font-semibold">{c.label}</div>
                <div className="text-xs text-slate-400">
                  {busy ? "Finding the one…" : "Surprise me"}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
