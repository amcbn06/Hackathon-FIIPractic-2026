// Category metadata shared across the UI.
export const CATEGORIES = [
  { key: "cafe", label: "Café", icon: "☕", tint: "from-amber-500/20 to-orange-500/10" },
  { key: "park", label: "Park", icon: "🌳", tint: "from-emerald-500/20 to-green-500/10" },
  { key: "museum", label: "Museum", icon: "🏛️", tint: "from-sky-500/20 to-blue-500/10" },
  { key: "bar", label: "Bar", icon: "🍻", tint: "from-yellow-500/20 to-amber-500/10" },
  { key: "restaurant", label: "Restaurant", icon: "🍽️", tint: "from-rose-500/20 to-pink-500/10" },
  { key: "viewpoint", label: "Viewpoint", icon: "🌆", tint: "from-indigo-500/20 to-violet-500/10" },
  { key: "sport", label: "Sport", icon: "⚽", tint: "from-lime-500/20 to-green-500/10" },
  { key: "entertainment", label: "Fun", icon: "🎭", tint: "from-fuchsia-500/20 to-purple-500/10" },
  { key: "cultural", label: "Culture", icon: "🎨", tint: "from-cyan-500/20 to-teal-500/10" },
];

export const CATEGORY_META = Object.fromEntries(
  CATEGORIES.map((c) => [c.key, c])
);

export function catIcon(key) {
  return CATEGORY_META[key]?.icon ?? "📍";
}
export function catLabel(key) {
  return CATEGORY_META[key]?.label ?? key;
}

export function mapUrl(lat, lon, name) {
  const q = encodeURIComponent(name || `${lat},${lon}`);
  return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=17/${lat}/${lon}`;
}

export function directionsUrl(lat, lon) {
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}`;
}
