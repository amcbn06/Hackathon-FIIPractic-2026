import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useToast, Spinner, EmptyState } from "../components/ui";
import { catIcon, catLabel, directionsUrl } from "../lib/constants";

export default function Result() {
  const { state } = useLocation();
  const navigate = useNavigate();
  const toast = useToast();

  const [pick, setPick] = useState(state?.pick || null);
  const isGroup = state?.group;
  const [rerolling, setRerolling] = useState(false);
  const [visiting, setVisiting] = useState(false);
  const [thumb, setThumb] = useState(0);
  const [visited, setVisited] = useState(pick?.visited || false);

  if (!pick) {
    return (
      <EmptyState
        icon="🎯"
        title="No pick yet"
        subtitle="Head back and choose a vibe to get your one recommendation."
        action={<Link to="/" className="btn-primary">Pick a vibe</Link>}
      />
    );
  }

  const reroll = async () => {
    setRerolling(true);
    try {
      const next = await api.reroll(pick.pick_id);
      setPick(next);
      setThumb(0);
      setVisited(false);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setRerolling(false);
    }
  };

  const markVisited = async () => {
    setVisiting(true);
    try {
      const res = await api.markVisited(pick.pick_id);
      setVisited(true);
      toast.success(`Visited! Streak: ${res.streak_current} 🔥`);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setVisiting(false);
    }
  };

  const setThumbs = async (value) => {
    const next = thumb === value ? 0 : value;
    setThumb(next);
    try {
      await api.thumbs(pick.pick_id, next);
    } catch (err) {
      toast.error(err.message);
    }
  };

  const bbox = `${pick.lon - 0.01},${pick.lat - 0.008},${pick.lon + 0.01},${pick.lat + 0.008}`;
  const mapSrc = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${pick.lat},${pick.lon}`;

  return (
    <div className="mx-auto max-w-2xl animate-pop-in space-y-5">
      <button onClick={() => navigate("/")} className="text-sm text-slate-400 hover:text-slate-200">
        ← Back to discover
      </button>

      <div className="card overflow-hidden">
        <div className="relative h-44 w-full bg-gradient-to-br from-brand-600/30 to-accent-500/20">
          {pick.photo_url ? (
            <img src={pick.photo_url} alt={pick.name} className="h-full w-full object-cover" />
          ) : (
            <div className="grid h-full place-items-center text-6xl opacity-80">
              {catIcon(pick.category)}
            </div>
          )}
          <div className="absolute left-4 top-4 flex gap-2">
            <span className="chip bg-black/40">{catIcon(pick.category)} {catLabel(pick.category)}</span>
            {isGroup && <span className="chip bg-brand-600/60 text-white">Group pick</span>}
          </div>
        </div>

        <div className="space-y-4 p-6">
          <div>
            <div className="label">Your one pick</div>
            <h1 className="mt-1 font-display text-2xl font-bold">{pick.name}</h1>
            {pick.address && <p className="text-sm text-slate-400">{pick.address}</p>}
          </div>

          <p className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm leading-relaxed text-slate-200">
            <span className="mr-1 text-brand-300">Why this?</span> {pick.why}
          </p>

          {pick.hours && (
            <div className="text-xs text-slate-400">🕒 {pick.hours}</div>
          )}

          <div className="overflow-hidden rounded-xl border border-white/10">
            <iframe
              title="map"
              src={mapSrc}
              className="h-52 w-full"
              loading="lazy"
            />
          </div>

          <div className="flex flex-wrap gap-2">
            <a href={directionsUrl(pick.lat, pick.lon)} target="_blank" rel="noreferrer" className="btn-primary flex-1">
              🧭 Directions
            </a>
            <button onClick={reroll} disabled={rerolling} className="btn-ghost flex-1">
              {rerolling ? <Spinner /> : "🎲 Reroll"}
            </button>
          </div>

          <div className="flex items-center justify-between gap-3 border-t border-white/10 pt-4">
            <div className="flex gap-2">
              <button
                onClick={() => setThumbs(1)}
                className={`btn-ghost ${thumb === 1 ? "!bg-emerald-600/30 !border-emerald-500/50" : ""}`}
              >
                👍 Worth it
              </button>
              <button
                onClick={() => setThumbs(-1)}
                className={`btn-ghost ${thumb === -1 ? "!bg-rose-600/30 !border-rose-500/50" : ""}`}
              >
                👎 Skip
              </button>
            </div>
            <button
              onClick={markVisited}
              disabled={visiting || visited}
              className={visited ? "btn-ghost !border-emerald-500/50 !text-emerald-300" : "btn-primary"}
            >
              {visiting ? <Spinner /> : visited ? "✓ Visited" : "I went here"}
            </button>
          </div>
          {isGroup && !visited && (
            <p className="text-center text-xs text-slate-500">
              Group picks count as visited once everyone checks in.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
