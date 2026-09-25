// Thin fetch wrapper around the South API.
// In dev, requests go to /api (proxied by Vite). In prod set VITE_API_URL.

const RAW_BASE = import.meta.env.VITE_API_URL;
// If VITE_API_URL is set we call it directly; otherwise use the dev proxy path.
const BASE = RAW_BASE && RAW_BASE.trim() ? RAW_BASE.replace(/\/$/, "") : "/api";

const TOKEN_KEY = "onepick_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(method, path, { body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const t = getToken();
    if (t) headers.Authorization = `Bearer ${t}`;
  }
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return null;

  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    const detail =
      (data && (data.detail || data.message)) ||
      (typeof data === "string" ? data : `Request failed (${res.status})`);
    const msg = Array.isArray(detail)
      ? detail.map((d) => d.msg || JSON.stringify(d)).join(", ")
      : detail;
    throw new ApiError(msg, res.status);
  }
  return data;
}

const get = (p, o) => request("GET", p, o);
const post = (p, body, o) => request("POST", p, { body, ...o });
const del = (p, o) => request("DELETE", p, o);

export const api = {
  // --- auth ---
  signup: (email, password, display_name) =>
    post("/signup", { email, password, display_name }, { auth: false }),
  login: (email, password) =>
    post("/login", { email, password }, { auth: false }),
  me: () => get("/me"),

  // --- discovery ---
  cities: () => get("/cities", { auth: false }),
  categories: (city) => get(`/categories${city ? `?city=${encodeURIComponent(city)}` : ""}`, { auth: false }),

  // --- picks ---
  pick: (category, city, group_id) => post("/pick", { category, city, group_id }),
  reroll: (pickId) => post(`/pick/${pickId}/reroll`),
  markVisited: (pickId) => post(`/pick/${pickId}/visited`),
  thumbs: (pickId, value) => post(`/pick/${pickId}/thumbs?value=${value}`),

  // --- places catalogue ---
  places: (params = {}) => {
    const q = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v != null && v !== "")
    ).toString();
    return get(`/places${q ? `?${q}` : ""}`);
  },
  pendingPlaces: (city) =>
    get(`/places/pending${city ? `?city=${encodeURIComponent(city)}` : ""}`),
  suggestPlace: (payload) => post("/places/suggest", payload),
  votePlace: (id) => post(`/places/${id}/vote`),
  approvePlace: (id) => post(`/places/${id}/approve`),
  rejectPlace: (id) => post(`/places/${id}/reject`),
  deletePlace: (id) => del(`/places/${id}`),

  // --- itinerary ---
  itinerary: (categories, city) => post("/itinerary", { categories, city }),
  saveItinerary: (city, stops) => post("/itinerary/save", { city, stops }),
  markStop: (stopId) => post(`/itinerary/stop/${stopId}/visited`),
  smartRoute: (categories, city) => post("/ai/smart-route", { categories, city }),

  // --- gamification ---
  streak: () => get("/me/streak"),
  streakCalendar: (days = 35) => get(`/me/streak/calendar?days=${days}`),
  history: (limit = 50) => get(`/me/history?limit=${limit}`),
  tracker: () => get("/me/tracker"),

  // --- friends ---
  friends: () => get("/friends"),
  pendingRequests: () => get("/friends/pending"),
  sendFriendRequest: (invite_code) => post("/friends/request", { invite_code }),
  acceptFriend: (requesterId) => post(`/friends/accept?requester_id=${requesterId}`),
  declineFriend: (requesterId) => post(`/friends/decline?requester_id=${requesterId}`),
  friendHistory: (friendId) => get(`/friends/${friendId}/history`),
  removeFriend: (friendId) => del(`/friends/${friendId}`),
  blockFriend: (friendId) => post(`/friends/${friendId}/block`),
  blockedUsers: () => get("/friends/blocked"),
  unblockUser: (friendId) => post(`/friends/${friendId}/unblock`),

  // --- groups ---
  groups: () => get("/groups"),
  createGroup: (name, member_ids = []) => post("/groups", { name, member_ids }),
  groupPick: (groupId, category, city) =>
    post(`/groups/${groupId}/pick`, { category, city }),
  inviteToGroup: (groupId, userId) => post(`/groups/${groupId}/invite?user_id=${userId}`),
  pendingGroupInvites: () => get("/groups/invites/pending"),
  acceptGroupInvite: (inviteId) => post(`/groups/invites/${inviteId}/accept`),
  declineGroupInvite: (inviteId) => post(`/groups/invites/${inviteId}/decline`),
  deleteGroup: (groupId) => del(`/groups/${groupId}`),
  kickMember: (groupId, userId) => del(`/groups/${groupId}/members/${userId}`),

  // --- custom spots ---
  customLocations: () => get("/custom-locations"),
  addCustomLocation: (payload) => post("/custom-locations", payload),
  deleteCustomLocation: (id) => del(`/custom-locations/${id}`),
};
